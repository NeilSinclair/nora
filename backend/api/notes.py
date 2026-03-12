"""REST endpoints for notes."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.api.deps import require_auth
from backend.config import settings
from backend.database import get_db
from backend.services import chroma_client, openai_client
from datetime import datetime, timezone

router = APIRouter(prefix="/notes", dependencies=[Depends(require_auth)])


class NoteCreate(BaseModel):
    content: str
    tags: list[str] = []


class NoteUpdate(BaseModel):
    content: str | None = None
    tags: list[str] | None = None


class NoteResponse(BaseModel):
    id: int
    filepath: str
    content: str
    tags: list[str]
    created_at: str
    updated_at: str


class NoteLink(BaseModel):
    note2_id: int
    relationship: str


def _read_note(filepath: str) -> str:
    p = Path(filepath)
    return p.read_text() if p.exists() else ""


@router.get("")
async def list_notes(archived: bool = False):
    base = settings.notes_archive_dir if archived else settings.notes_dir
    with get_db() as db:
        rows = db.execute(
            "SELECT id, filepath, created_at, updated_at FROM notes WHERE filepath LIKE ?",
            (f"%{'/archive/' if archived else '/notes/'}%",),
        ).fetchall()
    return [
        {
            "id": r["id"],
            "filepath": r["filepath"],
            "snippet": _read_note(r["filepath"])[:120],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }
        for r in rows
    ]


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(note_id: int):
    with get_db() as db:
        row = db.execute(
            "SELECT id, filepath, created_at, updated_at FROM notes WHERE id = ?", (note_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Note not found")
        tags = [t["tag"] for t in db.execute(
            "SELECT tag FROM tags WHERE note_id = ?", (note_id,)
        ).fetchall()]
    return NoteResponse(
        id=row["id"],
        filepath=row["filepath"],
        content=_read_note(row["filepath"]),
        tags=tags,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.post("", response_model=NoteResponse, status_code=201)
async def create_note(body: NoteCreate):
    from backend.handlers.notes import _new_filepath
    settings.notes_dir.mkdir(parents=True, exist_ok=True)
    filepath = _new_filepath()
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as db:
        cursor = db.execute(
            "INSERT INTO notes (filepath, created_at, updated_at) VALUES (?, ?, ?)",
            (str(filepath), now, now),
        )
        note_id = cursor.lastrowid
        if body.tags:
            db.executemany(
                "INSERT INTO tags (note_id, tag) VALUES (?, ?)",
                [(note_id, t) for t in body.tags],
            )
    filepath.write_text(body.content)
    embedding = await openai_client.get_embedding(body.content)
    await chroma_client.upsert_note(note_id, embedding, str(filepath))
    return NoteResponse(
        id=note_id, filepath=str(filepath), content=body.content,
        tags=body.tags, created_at=now, updated_at=now,
    )


@router.patch("/{note_id}", response_model=NoteResponse)
async def update_note(note_id: int, body: NoteUpdate):
    with get_db() as db:
        row = db.execute(
            "SELECT filepath, created_at FROM notes WHERE id = ?", (note_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Note not found")
        filepath = Path(row["filepath"])
        content = body.content if body.content is not None else _read_note(str(filepath))
        now = datetime.now(timezone.utc).isoformat()
        filepath.write_text(content)
        db.execute("UPDATE notes SET updated_at = ? WHERE id = ?", (now, note_id))
        if body.tags is not None:
            db.execute("DELETE FROM tags WHERE note_id = ?", (note_id,))
            db.executemany(
                "INSERT INTO tags (note_id, tag) VALUES (?, ?)",
                [(note_id, t) for t in body.tags],
            )
            tags = body.tags
        else:
            tags = [t["tag"] for t in db.execute(
                "SELECT tag FROM tags WHERE note_id = ?", (note_id,)
            ).fetchall()]
    embedding = await openai_client.get_embedding(content)
    await chroma_client.upsert_note(note_id, embedding, str(filepath))
    return NoteResponse(
        id=note_id, filepath=str(filepath), content=content,
        tags=tags, created_at=row["created_at"], updated_at=now,
    )


@router.delete("/{note_id}", status_code=204)
async def delete_note(note_id: int):
    import shutil
    with get_db() as db:
        row = db.execute("SELECT filepath FROM notes WHERE id = ?", (note_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Note not found")
        filepath = Path(row["filepath"])
        if filepath.exists():
            archive = settings.notes_archive_dir
            archive.mkdir(parents=True, exist_ok=True)
            shutil.move(str(filepath), str(archive / filepath.name))
        db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    await chroma_client.delete_note(note_id)


@router.post("/{note_id}/links")
async def link_notes(note_id: int, body: NoteLink):
    with get_db() as db:
        for nid in [note_id, body.note2_id]:
            if not db.execute("SELECT id FROM notes WHERE id = ?", (nid,)).fetchone():
                raise HTTPException(status_code=404, detail=f"Note {nid} not found")
        db.execute(
            "INSERT INTO relationships (note1_id, relationship, note2_id) VALUES (?, ?, ?)",
            (note_id, body.relationship, body.note2_id),
        )
    return {"ok": True}


@router.get("/{note_id}/connections")
async def get_connections(note_id: int):
    with get_db() as db:
        linked = db.execute(
            """
            SELECT r.relationship, n.id, n.filepath
            FROM relationships r
            JOIN notes n ON n.id = CASE WHEN r.note1_id = ? THEN r.note2_id ELSE r.note1_id END
            WHERE r.note1_id = ? OR r.note2_id = ?
            """,
            (note_id, note_id, note_id),
        ).fetchall()
    # Suggested notes via semantic search
    with get_db() as db:
        row = db.execute("SELECT filepath FROM notes WHERE id = ?", (note_id,)).fetchone()
    suggested = []
    if row and Path(row["filepath"]).exists():
        content = Path(row["filepath"]).read_text()
        embedding = await openai_client.get_embedding(content[:500])
        candidates = await chroma_client.search_notes(embedding, limit=6)
        suggested = [c for c in candidates if c["note_id"] != note_id][:5]

    return {
        "linked": [
            {"note_id": r["id"], "filepath": r["filepath"], "relationship": r["relationship"]}
            for r in linked
        ],
        "suggested": suggested,
    }
