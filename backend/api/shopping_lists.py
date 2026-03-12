"""REST endpoints for shopping lists."""

import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.api.deps import require_auth
from backend.config import settings
from backend.database import get_db

router = APIRouter(prefix="/shopping-lists", dependencies=[Depends(require_auth)])


class ShoppingListCreate(BaseModel):
    content: str


class ShoppingListUpdate(BaseModel):
    content: str


@router.get("")
async def list_shopping_lists(archived: bool = False):
    base = settings.shopping_lists_archive_dir if archived else settings.shopping_lists_dir
    if not base.exists():
        return []
    files = sorted(base.glob("*.txt"), reverse=True)
    with get_db() as db:
        results = []
        for f in files:
            row = db.execute(
                "SELECT id, created_at FROM shopping_lists WHERE filepath = ?", (str(f),)
            ).fetchone()
            results.append({
                "id": row["id"] if row else None,
                "filepath": str(f),
                "date": f.stem,
                "snippet": f.read_text()[:120],
            })
    return results


@router.get("/{list_id}")
async def get_shopping_list(list_id: int):
    with get_db() as db:
        row = db.execute(
            "SELECT id, filepath, created_at FROM shopping_lists WHERE id = ?", (list_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Shopping list not found")
    filepath = Path(row["filepath"])
    return {
        "id": row["id"],
        "filepath": row["filepath"],
        "content": filepath.read_text() if filepath.exists() else "",
        "created_at": row["created_at"],
    }


@router.post("", status_code=201)
async def create_shopping_list(body: ShoppingListCreate):
    settings.shopping_lists_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    filepath = settings.shopping_lists_dir / f"{date_str}.txt"
    # Append if today's list already exists
    with filepath.open("a") as f:
        if filepath.stat().st_size > 0 if filepath.exists() else False:
            f.write("\n")
        f.write(body.content)
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as db:
        existing = db.execute(
            "SELECT id FROM shopping_lists WHERE filepath = ?", (str(filepath),)
        ).fetchone()
        if existing:
            list_id = existing["id"]
        else:
            cursor = db.execute(
                "INSERT INTO shopping_lists (filepath, created_at) VALUES (?, ?)",
                (str(filepath), now),
            )
            list_id = cursor.lastrowid
    return {"id": list_id, "filepath": str(filepath)}


@router.patch("/{list_id}")
async def update_shopping_list(list_id: int, body: ShoppingListUpdate):
    with get_db() as db:
        row = db.execute(
            "SELECT filepath FROM shopping_lists WHERE id = ?", (list_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Shopping list not found")
    Path(row["filepath"]).write_text(body.content)
    return {"ok": True}


@router.delete("/{list_id}", status_code=204)
async def delete_shopping_list(list_id: int):
    with get_db() as db:
        row = db.execute(
            "SELECT filepath FROM shopping_lists WHERE id = ?", (list_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Shopping list not found")
        filepath = Path(row["filepath"])
        if filepath.exists():
            archive = settings.shopping_lists_archive_dir
            archive.mkdir(parents=True, exist_ok=True)
            shutil.move(str(filepath), str(archive / filepath.name))
        db.execute("DELETE FROM shopping_lists WHERE id = ?", (list_id,))
