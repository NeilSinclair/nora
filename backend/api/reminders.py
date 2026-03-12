"""REST endpoints for reminders."""

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.api.deps import require_auth
from backend.config import settings

router = APIRouter(prefix="/reminders", dependencies=[Depends(require_auth)])


class ReminderCreate(BaseModel):
    text: str
    remind_at: str  # ISO datetime string


class ReminderUpdate(BaseModel):
    text: str | None = None
    remind_at: str | None = None


def _load() -> list[dict]:
    path = settings.reminders_file
    if not path.exists():
        return []
    return json.loads(path.read_text()).get("reminders", [])


def _save(reminders: list[dict]) -> None:
    settings.reminders_file.parent.mkdir(parents=True, exist_ok=True)
    settings.reminders_file.write_text(json.dumps({"reminders": reminders}, indent=2))


@router.get("")
async def list_reminders():
    return {"reminders": _load()}


@router.post("", status_code=201)
async def create_reminder(body: ReminderCreate):
    reminders = _load()
    reminder = {
        "id": str(uuid.uuid4()),
        "text": body.text,
        "remind_at": body.remind_at,
        "sent": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    reminders.append(reminder)
    _save(reminders)
    return reminder


@router.patch("/{reminder_id}")
async def update_reminder(reminder_id: str, body: ReminderUpdate):
    reminders = _load()
    for r in reminders:
        if r["id"] == reminder_id:
            if body.text is not None:
                r["text"] = body.text
            if body.remind_at is not None:
                r["remind_at"] = body.remind_at
                r["sent"] = False
            _save(reminders)
            return r
    raise HTTPException(status_code=404, detail="Reminder not found")


@router.delete("/{reminder_id}", status_code=204)
async def delete_reminder(reminder_id: str):
    reminders = _load()
    updated = [r for r in reminders if r["id"] != reminder_id]
    if len(updated) == len(reminders):
        raise HTTPException(status_code=404, detail="Reminder not found")
    _save(updated)
