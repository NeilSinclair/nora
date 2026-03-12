"""Shopping lists handler: CRUD on flat files + SQLite metadata."""

import shutil
from datetime import datetime, timezone

from backend.config import settings
from backend.database import get_db
from backend.pipeline.models import PipelineContext, ShoppingListsIntentOutput


def _filepath_for_today() -> str:
    return str(settings.shopping_lists_dir / f"{datetime.now().strftime('%Y%m%d')}.txt")


async def handle(ctx: PipelineContext) -> str:
    """Execute the shopping list intent.

    Args:
      ctx (PipelineContext): Pipeline context; intent_data must be ShoppingListsIntentOutput.

    Returns:
      str: Human-readable result.
    """
    intent_data: ShoppingListsIntentOutput = ctx.intent_data  # type: ignore[assignment]

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
            return "I'm not sure what you want to do with your shopping lists."


async def _add(intent_data: ShoppingListsIntentOutput) -> str:
    if not intent_data.content:
        return "What should be on the shopping list?"
    settings.shopping_lists_dir.mkdir(parents=True, exist_ok=True)
    filepath = _filepath_for_today()
    path = settings.DATA_DIR.parent / filepath if not filepath.startswith("/") else \
        settings.shopping_lists_dir / filepath.split("/")[-1]
    # Append to today's list if it already exists
    full_path = settings.shopping_lists_dir / f"{datetime.now().strftime('%Y%m%d')}.txt"
    mode = "a" if full_path.exists() else "w"
    with full_path.open(mode) as f:
        if mode == "a":
            f.write("\n" + intent_data.content)
        else:
            f.write(intent_data.content)

    now = datetime.now(timezone.utc).isoformat()
    with get_db() as db:
        existing = db.execute(
            "SELECT id FROM shopping_lists WHERE filepath = ?", (str(full_path),)
        ).fetchone()
        if not existing:
            db.execute(
                "INSERT INTO shopping_lists (filepath, created_at) VALUES (?, ?)",
                (str(full_path), now),
            )
    return "Shopping list updated."


async def _edit(intent_data: ShoppingListsIntentOutput) -> str:
    if not intent_data.list_id or not intent_data.content:
        return "Please specify which list to edit and the new content."
    with get_db() as db:
        row = db.execute(
            "SELECT filepath FROM shopping_lists WHERE id = ?", (intent_data.list_id,)
        ).fetchone()
    if not row:
        return f"Shopping list {intent_data.list_id} not found."
    from pathlib import Path
    Path(row["filepath"]).write_text(intent_data.content)
    return "Shopping list updated."


async def _delete(intent_data: ShoppingListsIntentOutput) -> str:
    if not intent_data.list_id:
        return "Which shopping list would you like to delete?"
    with get_db() as db:
        row = db.execute(
            "SELECT filepath FROM shopping_lists WHERE id = ?", (intent_data.list_id,)
        ).fetchone()
        if not row:
            return f"Shopping list {intent_data.list_id} not found."
        from pathlib import Path
        filepath = Path(row["filepath"])
        if filepath.exists():
            # Archive instead of hard delete
            archive = settings.shopping_lists_archive_dir
            archive.mkdir(parents=True, exist_ok=True)
            shutil.move(str(filepath), str(archive / filepath.name))
        db.execute("DELETE FROM shopping_lists WHERE id = ?", (intent_data.list_id,))
    return "Shopping list archived."


async def _search(intent_data: ShoppingListsIntentOutput) -> str:
    base_dir = settings.shopping_lists_archive_dir if intent_data.archived \
        else settings.shopping_lists_dir
    if not base_dir.exists():
        return "No shopping lists found."
    term = (intent_data.contextual_search_term or "").lower()
    results = []
    for f in sorted(base_dir.glob("*.txt"), reverse=True):
        content = f.read_text()
        if not term or term in content.lower():
            results.append(f"**{f.stem}**\n{content[:200]}")
    if not results:
        return "No matching shopping lists found."
    return "\n\n".join(results[:5])


async def _list_all(intent_data: ShoppingListsIntentOutput) -> str:
    base_dir = settings.shopping_lists_archive_dir if intent_data.archived \
        else settings.shopping_lists_dir
    if not base_dir.exists():
        return "No shopping lists found."
    files = sorted(base_dir.glob("*.txt"), reverse=True)
    if not files:
        return "No shopping lists found."
    summaries = [f"- {f.stem}" for f in files[:10]]
    return "Shopping lists:\n" + "\n".join(summaries)
