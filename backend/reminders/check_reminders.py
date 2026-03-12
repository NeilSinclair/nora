"""Standalone cron script: send due reminders via Telegram.

Set up via system cron to run every minute:
  * * * * * cd /path/to/nora && python -m backend.reminders.check_reminders

The script is intentionally self-contained — it does not import FastAPI or the bot process.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from telegram import Bot

from backend.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _load() -> list[dict]:
    path = settings.reminders_file
    if not path.exists():
        return []
    return json.loads(path.read_text()).get("reminders", [])


def _save(reminders: list[dict]) -> None:
    settings.reminders_file.write_text(json.dumps({"reminders": reminders}, indent=2))


async def check_and_send() -> None:
    reminders = _load()
    now = datetime.now(timezone.utc)
    changed = False

    due = [r for r in reminders if not r["sent"] and r.get("remind_at")]
    if not due:
        return

    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)

    for reminder in due:
        try:
            remind_at = datetime.fromisoformat(reminder["remind_at"])
            # Ensure timezone-aware for comparison
            if remind_at.tzinfo is None:
                remind_at = remind_at.replace(tzinfo=timezone.utc)
        except ValueError:
            logger.warning("Invalid remind_at for reminder %s", reminder["id"])
            continue

        if remind_at <= now:
            try:
                # Reminders are always sent to the single user; use the chat_id stored at creation.
                # For now we use the TELEGRAM_BOT_TOKEN owner's chat — the user_id must be stored
                # in the reminder or configured. Here we expect reminder["chat_id"] if set.
                chat_id = reminder.get("chat_id")
                if not chat_id:
                    logger.warning("No chat_id for reminder %s; skipping", reminder["id"])
                    continue
                await bot.send_message(chat_id=chat_id, text=f"⏰ Reminder: {reminder['text']}")
                reminder["sent"] = True
                changed = True
                logger.info("Sent reminder %s", reminder["id"])
            except Exception as e:
                logger.error("Failed to send reminder %s: %s", reminder["id"], e)

    if changed:
        _save(reminders)


if __name__ == "__main__":
    asyncio.run(check_and_send())
