"""Reminders handler: CRUD on data/reminders/reminders.json."""

import json
import uuid
from datetime import datetime, timezone

from backend.config import settings
from backend.pipeline.models import PipelineContext, RemindersIntentOutput


def _load() -> list[dict]:
    path = settings.reminders_file
    if not path.exists():
        return []
    return json.loads(path.read_text()).get("reminders", [])


def _save(reminders: list[dict]) -> None:
    settings.reminders_file.parent.mkdir(parents=True, exist_ok=True)
    settings.reminders_file.write_text(json.dumps({"reminders": reminders}, indent=2))


async def handle(ctx: PipelineContext) -> str:
    """Execute the reminders intent.

    Args:
      ctx (PipelineContext): Pipeline context; intent_data must be RemindersIntentOutput.

    Returns:
      str: Human-readable result.
    """
    intent_data: RemindersIntentOutput = ctx.intent_data  # type: ignore[assignment]
    reminders = _load()

    match intent_data.intent:
        case "add":
            if not intent_data.text or not intent_data.remind_at:
                return "Please tell me what to remind you about and when."
            reminder = {
                "id": str(uuid.uuid4()),
                "text": intent_data.text,
                "remind_at": intent_data.remind_at,
                "sent": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
                # chat_id stored so the cron script knows where to send the Telegram message.
                # For web UI users this will be None; cron will skip those.
                "chat_id": ctx.user_id if ctx.user_id != "web" else None,
            }
            reminders.append(reminder)
            _save(reminders)
            return f"Reminder set: \"{intent_data.text}\" at {intent_data.remind_at}."

        case "edit":
            if not intent_data.reminder_id:
                return "Which reminder would you like to edit? Please specify the ID."
            for r in reminders:
                if r["id"] == intent_data.reminder_id:
                    if intent_data.text:
                        r["text"] = intent_data.text
                    if intent_data.remind_at:
                        r["remind_at"] = intent_data.remind_at
                        r["sent"] = False  # Re-arm if time changed
                    _save(reminders)
                    return f"Reminder updated."
            return f"Reminder {intent_data.reminder_id} not found."

        case "delete":
            if not intent_data.reminder_id:
                return "Which reminder would you like to delete? Please specify the ID."
            before = len(reminders)
            reminders = [r for r in reminders if r["id"] != intent_data.reminder_id]
            if len(reminders) == before:
                return f"Reminder {intent_data.reminder_id} not found."
            _save(reminders)
            return "Reminder deleted."

        case "list":
            pending = [r for r in reminders if not r["sent"]]
            if not pending:
                return "You have no upcoming reminders."
            lines = [f"- [{r['id'][:8]}] {r['text']} → {r['remind_at']}" for r in pending]
            return "Upcoming reminders:\n" + "\n".join(lines)

        case _:
            return "I'm not sure what you want to do with your reminders."
