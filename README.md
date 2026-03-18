# Nora

An AI notetaker and calendar manager, accessible via Telegram bot and a React web app. See `SPEC.md` for the full specification.

## Setup

**1. Install dependencies**
```bash
uv sync
```

**2. Configure environment**
```bash
cp .env.example .env
# Fill in your values
```

**3. Set up Google Calendar**

Create a service account in Google Cloud Console, download the JSON key, and share your Google Calendar with the service account email. Set `GOOGLE_SERVICE_ACCOUNT_FILE` and `GOOGLE_CALENDAR_ID` in `.env`.

## Running

The backend runs as two separate processes:

**FastAPI server** (REST API + web UI backend)
```bash
uv run uvicorn backend.main:app --reload
```

**Telegram bot** (long polling)
```bash
uv run python -m backend.telegram.bot
```

**Reminder cron** — add to system crontab to run every minute:
```
* * * * * cd /path/to/nora && uv run python -m backend.reminders.check_reminders
```

## Development

```bash
uv run pytest          # run tests
uv run ruff check .    # lint
uv run ruff format .   # format
```

## Data

All runtime data is stored in `data/` (gitignored):
- Notes: `data/notes/`
- Shopping lists: `data/shopping_lists/`
- Reminders: `data/reminders/reminders.json`
- Database: `data/nora.db` (SQLite)
- Embeddings: `data/chroma/` (ChromaDB)
