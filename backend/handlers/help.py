"""Help handler: returns a static description of Nora's capabilities."""

from backend.pipeline.models import PipelineContext

_HELP_TEXT = """
Here's what I can help you with:

📝 **Notes** — add, edit, delete, search (by keyword or tags), archive
📋 **Shopping lists** — add, edit, delete, search by date, archive
⏰ **Reminders** — add, edit, delete; I'll message you at the right time
📅 **Calendar** — add, edit, delete and view Google Calendar events
💬 **Chat** — ask me anything

**Tips:**
- You can use voice notes from Telegram, or type to me here.
- Say "voice on" or "voice off" to toggle spoken responses.
- In the web app, click Notes / Reminders / Calendar to browse your data.
""".strip()


async def handle(ctx: PipelineContext) -> str:
    return _HELP_TEXT
