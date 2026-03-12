# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Nora** is an AI notetaker and calendar manager accessible via a Telegram bot and a React web app. See `SPEC.md` for the full product specification.

## Commands

The project has not been scaffolded yet. When building out the backend (Python) and frontend (React), use these conventions:

**Backend:**
```bash
# Lint
ruff check .
ruff format .

# Tests
pytest                        # all tests
pytest tests/test_foo.py      # single file
pytest tests/test_foo.py::test_name  # single test
```

**Frontend:**
```bash
# Standard React/npm commands (to be set up)
npm install
npm run dev
npm run build
npm test
```

## Architecture

### Backend (Python)

The backend is structured around a **router → intent parser → handler** pipeline:

1. **Router** (`ROUTER_LLM = gpt-5-nano`) — Uses OpenAI Structured Outputs to classify incoming messages into routes: `calendar`, `notes`, `reminders`, `shopping_lists`, `chat`, `help`. Captures optional `date_from`, `date_to`, and contextual metadata.

2. **Intent Parser** (`INTENT_PARSER = gpt-5-nano`) — Within each route, decodes user intent (add/edit/delete/search) using structured outputs. For searches, captures a contextual search term (e.g. if conversation was about IKEA and user says "yes, but tables" → term is "tables at IKEA"), tags, date ranges, archive flag, and whether LLM post-processing is needed.

3. **Handlers** — Execute the action (CRUD on files/DB, calendar API calls, etc.), optionally apply an LLM pass if the intent parser flagged it, then return a response.

Conversation history: last `HISTORY_LENGTH` (default 3) turns for both user and assistant, stored in a config file.

**Input modalities:** Text and voice (Telegram voice notes transcribed via Whisper before routing). Voice responses use Whisper TTS and are toggled per-user preference.

### Data Storage

| Store | Path / Location |
|---|---|
| Notes (content) | `data/notes/YYMMDD-HHMM.txt` |
| Archived notes | `data/notes/archive/` |
| Shopping lists (content) | `data/shopping_lists/<date>.txt` |
| Archived shopping lists | `data/shopping_lists/archive/` |
| Reminders | `data/reminders/reminders.json` |
| Note/list metadata, tags, relationships | `data/nora.db` (SQLite) |
| Embeddings | Qdrant (local instance) |
| Conversation history + voice preference | `data/state.json` (offline analysis only; not reloaded on restart) |

SQLite schema:
```sql
notes(id, filepath, created_at, updated_at)
tags(id, note_id, tag)
relationships(id, note1_id, relationship, note2_id)
shopping_lists(id, filepath, created_at)
```

Reminders are triggered via a **system cron job** (separate process) running `reminders/check_reminders.py` every minute.

Semantic search uses Qdrant embeddings (`text-embedding-3-small`). Embeddings are generated on note save. Tag-based search is a separate path; both can be combined.

Google Calendar uses a **service account**; the user shares their calendar with the service account.

Telegram uses **long polling** (no webhook, no public HTTPS URL required).

### Frontend (React)

Stack: Vite + React 18.

Layout:
- **Left sidebar (60%)** — Chat panel with text + voice input/output
- **Main area** — Notes / Calendar / Reminders views (toggled by sidebar buttons)

Notes view has three panels: search results list → note editor (**Save button**; embeddings generated on save) → connections sidebar (linked + suggested notes). Note linking: drag-and-drop, "Link note" button, or `[[` inline syntax.

Login: password-only (set via `PASSWORD` env var). On success, a signed JWT is issued and stored as an HttpOnly cookie (`JWT_SECRET`).

### Key Config Variables

All stored in a config file (not hardcoded):

| Variable | Default | Description |
|---|---|---|
| `ROUTER_LLM` | `gpt-5-nano` | Model for routing |
| `INTENT_PARSER` | `gpt-5-nano` | Model for intent parsing |
| `HISTORY_LENGTH` | `3` | Conversation turns to retain |
| `PASSWORD` | — | UI login password |
| `JWT_SECRET` | — | Signs session JWTs |
| `TELEGRAM_BOT_TOKEN` | — | Telegram bot token |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | — | Path to Google service account JSON |
| `QDRANT_HOST` | `localhost` | Qdrant host |
| `QDRANT_PORT` | `6333` | Qdrant port |

### Key Dependencies

**Backend (Python):**
- `python-telegram-bot` with job-queue
- `openai` (Responses API + Embeddings — not Chat Completions)
- `fastapi`
- `qdrant-client`
- `python-jose` (JWT)
- `sqlite3` (stdlib)
- `ruff` for linting
- `pytest` for tests

**Frontend:**
- Vite + React 18

## Coding Conventions

### Comments
Conservative and concise. Only comment where an operation isn't obviously clear.

### Folder Structure
```
backend/    # Python backend (FastAPI)
frontend/   # React frontend (Vite + React 18)
data/       # Runtime data (notes, reminders, etc.)
tests/      # pytest unit tests
```

### Docstrings
```python
def function_name(parameter_1: type, parameter_2: type) -> ReturnType:
    """Summary of what the function does.
    More detailed description if necessary.

    Args:
      parameter_1 (type): description.
      parameter_2 (type): description.

    Returns:
      ReturnType: description.
    """
```

## Available Skills

This repo includes two Claude Code skills (not part of the Nora app):
- `frontend-design/` — Generates production-grade, distinctive React/HTML/CSS UIs
- `skill-creator/` — Creates and iteratively improves Claude Code skills with evals
