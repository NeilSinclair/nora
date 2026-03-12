"""Notes handler: CRUD on flat files + SQLite metadata + Qdrant embeddings."""

import random
import shutil
import string
from datetime import datetime, timezone
from pathlib import Path

from backend.config import settings
from backend.database import get_db
from backend.pipeline.models import NotesIntentOutput, PipelineContext
from backend.services import chroma_client, openai_client


def _new_filepath() -> Path:
    """Generate a unique note filepath using timestamp + random suffix."""
    ts = datetime.now().strftime("%y%m%d-%H%M%S")
    suffix = "".join(random.choices(string.ascii_lowercase, k=3))
    return settings.notes_dir / f"{ts}-{suffix}.txt"


async def _save_note_with_embedding(note_id: int, filepath: Path, content: str) -> None:
    """Write content to disk, generate embedding, upsert into Qdrant, update SQLite."""
    filepath.write_text(content)
    embedding = await openai_client.get_embedding(content)
    await chroma_client.upsert_note(note_id, embedding, str(filepath))
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as db:
        db.execute("UPDATE notes SET updated_at = ? WHERE id = ?", (now, note_id))


async def handle(ctx: PipelineContext) -> str:
    """Execute the notes intent.

    Args:
      ctx (PipelineContext): Pipeline context; intent_data must be NotesIntentOutput.

    Returns:
      str: Human-readable result.
    """
    intent_data: NotesIntentOutput = ctx.intent_data  # type: ignore[assignment]

    match intent_data.intent:
        case "add":
            return await _add(intent_data)
        case "edit":
            return await _edit(intent_data)
        case "delete":
            return await _delete(intent_data)
        case "search":
            return await _search(intent_data)
        case "list":
            return await _list_all(intent_data)
        case _:
            return "I'm not sure what you want to do with your notes."


async def _add(intent_data: NotesIntentOutput) -> str:
    if not intent_data.content:
        return "What should the note say?"
    settings.notes_dir.mkdir(parents=True, exist_ok=True)
    filepath = _new_filepath()
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as db:
        cursor = db.execute(
            "INSERT INTO notes (filepath, created_at, updated_at) VALUES (?, ?, ?)",
            (str(filepath), now, now),
        )
        note_id = cursor.lastrowid
        if intent_data.tags:
            db.executemany(
                "INSERT INTO tags (note_id, tag) VALUES (?, ?)",
                [(note_id, t) for t in intent_data.tags],
            )
    await _save_note_with_embedding(note_id, filepath, intent_data.content)
    return f"Note saved ({filepath.name})."


async def _edit(intent_data: NotesIntentOutput) -> str:
    if not intent_data.note_id or not intent_data.content:
        return "Please specify which note to edit and the new content."
    with get_db() as db:
        row = db.execute(
            "SELECT filepath FROM notes WHERE id = ?", (intent_data.note_id,)
        ).fetchone()
        if not row:
            return f"Note {intent_data.note_id} not found."
        filepath = Path(row["filepath"])
        # Update tags if provided
        if intent_data.tags:
            db.execute("DELETE FROM tags WHERE note_id = ?", (intent_data.note_id,))
            db.executemany(
                "INSERT INTO tags (note_id, tag) VALUES (?, ?)",
                [(intent_data.note_id, t) for t in intent_data.tags],
            )
    await _save_note_with_embedding(intent_data.note_id, filepath, intent_data.content)
    return "Note updated."


async def _delete(intent_data: NotesIntentOutput) -> str:
    if not intent_data.note_id:
        return "Which note would you like to delete?"
    with get_db() as db:
        row = db.execute(
            "SELECT filepath FROM notes WHERE id = ?", (intent_data.note_id,)
        ).fetchone()
        if not row:
            return f"Note {intent_data.note_id} not found."
        filepath = Path(row["filepath"])
        if filepath.exists():
            archive = settings.notes_archive_dir
            archive.mkdir(parents=True, exist_ok=True)
            shutil.move(str(filepath), str(archive / filepath.name))
        db.execute("DELETE FROM notes WHERE id = ?", (intent_data.note_id,))
    await chroma_client.delete_note(intent_data.note_id)
    return "Note archived."


async def _search(intent_data: NotesIntentOutput) -> str:
    results = []

    if intent_data.tags:
        # Tag-based search
        placeholders = ",".join("?" * len(intent_data.tags))
        with get_db() as db:
            rows = db.execute(
                f"""
                SELECT DISTINCT n.id, n.filepath FROM notes n
                JOIN tags t ON t.note_id = n.id
                WHERE t.tag IN ({placeholders})
                {"AND n.filepath LIKE '%/archive/%'" if intent_data.archived else
                 "AND n.filepath NOT LIKE '%/archive/%'"}
                LIMIT 10
                """,
                intent_data.tags,
            ).fetchall()
        results = [{"note_id": r["id"], "filepath": r["filepath"]} for r in rows]

    if intent_data.contextual_search_term and not results:
        # Semantic search
        embedding = await openai_client.get_embedding(intent_data.contextual_search_term)
        results = await chroma_client.search_notes(embedding, limit=10)

    if not results:
        return "No matching notes found."

    lines = []
    for r in results[:5]:
        filepath = Path(r["filepath"])
        snippet = filepath.read_text()[:120].replace("\n", " ") if filepath.exists() else ""
        lines.append(f"[{r['note_id']}] {filepath.name}: {snippet}…")
    return "Found notes:\n" + "\n".join(lines)


async def _list_all(intent_data: NotesIntentOutput) -> str:
    base = settings.notes_archive_dir if intent_data.archived else settings.notes_dir
    if not base.exists():
        return "No notes found."
    files = sorted(base.glob("*.txt"), reverse=True)
    if not files:
        return "No notes found."
    return "Notes:\n" + "\n".join(f"- {f.name}" for f in files[:10])
