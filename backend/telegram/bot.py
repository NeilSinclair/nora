"""Telegram bot entry point. Run as a standalone process.

Run with: python -m backend.telegram.bot
"""

import asyncio
import logging

from telegram.ext import ApplicationBuilder, MessageHandler, filters

from backend.config import settings
from backend.database import init_db
from backend.services.chroma_client import init_chroma
from backend.telegram.handlers import handle_text, handle_voice
from backend import state

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    init_db()
    init_chroma()
    state.load_preferences()

    app = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    logger.info("Nora Telegram bot starting (long polling)…")
    await app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
