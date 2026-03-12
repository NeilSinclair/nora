# Nora - AI Notetaker

## Project Overview
Nora is a single-user AI notetaker and calendar manager accessible through two interfaces: a Telegram bot and a React web app. Nora enables the user to do various organisational and note-taking tasks as outlined below.

Deployment: Hetzner VPS, always-on.

## Backend Functionality

The user can communicate with Nora using both text and voice notes from Telegram. The user can turn on (or off) voice responses from Nora by indicating that the user wants Nora to speak (or not speak) back. The user does this by saying something like "I want voice responses on" or "please speak send me voice notes".

### Calendar

- Add, delete, edit, read calendar items for a Google Calendar accessed through the Google Calendar API
- Google Calendar auth uses a service account; the user shares their calendar with the service account

### Notes

- Add, edit, delete notes
- Tag notes
- Notes can be linked with a relationship `<note1> -> <relationship> -> <note2>`. The user can ask for all related notes to a note, however the linking can only be done in the UI.
- Search notes via tags and/or semantic search. Search is automatically semantic, unless the user specifies they want to search notes with tags (e.g. "show me the notes tagged about my Apartment"). Search can be semantic and tag-based if the user asks for a search about something with certain tags, e.g. "Show me notes about features tagged with 'backend'".
- Notes are saved at `data/notes/YYMMDD-HHMM.txt`
- Notes can be archived; archived notes are stored in `data/notes/archive/`
- Note metadata (tags and relationships) is stored in SQLite at `data/nora.db`; note content stays in flat files

### Shopping Lists

- Add, edit, delete shopping lists
- Shopping lists are saved in `data/shopping_lists/<date>.txt`
- Shopping lists can be archived; archived lists are stored in `data/shopping_lists/archive/`
- Shopping list metadata is stored in the same SQLite DB as notes

### Reminders

- Add, edit and delete reminders
- Reminders are stored in `data/reminders/reminders.json`
- Reminders are sent to the user through Telegram via a system cron job (separate process) that runs every minute and polls `reminders.json`

### Help

- The user receives a pre-written message indicating what actions are possible with Nora

### Free-form chat

- If the user has a query that doesn't fit into any of the other routes, free-form chat is activated where the user speaks directly with an LLM
- Nora's persona in free-form chat is friendly and concise

## UI Functionality

The UI is a React web app (Vite + React 18). The chat section is on the left-hand side as a sidebar taking up 60% of the screen width. Below the chat area are three buttons — Notes, Reminders, Calendar — which bring up the relevant screen in the main area on the right.

### Chat section

On the left is a chat side panel where the user can chat with Nora. The AI it chats with is the same as the Telegram bot. The user can send text and voice messages and receive back text and voice messages. For voice messages, the user clicks a microphone button to record. When a voice message comes back it plays automatically, but is also shown with a play button for replay.

### Notes

The user can search for notes by chatting to Nora. Notes can be returned via tag or semantic search (see Backend Functionality).

1. **Search** → list of notes (left panel inside the main screen area, does not overlap the chat sidebar). Type to search; results appear as a simple vertical list: title and a short snippet.

2. **Selected note** → editor/viewer (centre panel inside the main screen area). When you click a note it opens in the middle. There is an explicit **Save button**; embeddings are generated on save via a backend API call.

3. **Connections sidebar** (right panel inside the main screen area). Shows two sections:
   - Linked notes
   - Suggested notes (via search or embeddings)

   Each item is a small card with the title.

**How linking works:**
- Drag a note from the search list onto the open note.
- Or click "Link note" → small search popup → select note.
- Or type `[[` inside the note (Notion/Obsidian style) and pick a result. Options shown are note titles.

Shopping lists are stored under notes. They do not have a title, are not connected to other notes, and can be searched for by date.

### Calendar

A React calendar widget showing calendar items in the main display area. Functionally similar to Google Calendar: navigate across months, click dates, and add/edit/delete/read calendar items.

### Reminders

A React widget in the main display area showing reminders with their scheduled date and time. The user can add, edit, and delete reminders.

### Login

A basic login screen with a password field. The password is set via the `PASSWORD` env var. On successful login, a signed JWT is issued and stored as an HttpOnly cookie for session persistence. The JWT is signed with `JWT_SECRET`.

## User Workflow Overview

Conversation history includes the last `HISTORY_LENGTH` (default 3) turns for both the user and the assistant. This enables contextual responses. Conversation history and voice preference are persisted to `data/state.json` for offline analysis; they are **not** reloaded into memory on restart.

### Telegram

Telegram uses **long polling** (no webhook; no public HTTPS URL required).

When interacting with the bot the workflow is:

1. The user sends a message (text or voice) to the bot
2. Voice messages are transcribed to text via Whisper
3. The message is passed to the **Router** (structured output, Responses API) which classifies it into one of: `calendar`, `notes`, `reminders`, `shopping_lists`, `chat`, `help`. The router also captures optional `date_from`, `date_to`, and `extra_context` fields.
4. Within `calendar`, `notes`, `reminders`, `shopping_lists` a structured output **Intent Parser** deciphers the user's intent (`add`, `edit`, `delete`, `search`, `list`). For searches it also captures: `contextual_search_term` (e.g. if conversation was about IKEA and user says "yes, but tables" → term is "tables at IKEA"), `tags`, date ranges, `archived` flag, and `llm_post_process: bool`.
5. The relevant **Handler** executes the action (CRUD on files/DB, calendar API calls, etc.). If `llm_post_process` is true, an LLM pass is applied before returning the response.
6. The response is returned as text or TTS voice depending on the user's preference.

### React UI

- The React app starts on the login screen where the user types their password. On success a signed JWT HttpOnly cookie is set.
- The user communicates with Nora by writing to it or recording voice notes. Voice messages are transcribed then sent to the backend as text. TTS voice responses work the same way as Telegram.
- The chat panel calls the same backend endpoints as the Telegram bot.
- The user can navigate the app to view and manage notes, calendar events, reminders, and shopping lists via the REST API.

## Architecture Deepdive

LLM provider: OpenAI, using the Responses API (not Chat Completions).

Config variables:
- `ROUTER_LLM = gpt-5-nano`
- `INTENT_PARSER = gpt-5-nano`

### System Components

| Component | Description |
|---|---|
| **Telegram bot process** | Long-polling bot; receives updates, calls backend logic |
| **React/FastAPI backend process** | Serves the React app and REST API; handles all AI logic |
| **System cron process** | Runs `reminders/check_reminders.py` every minute |
| **Qdrant instance** | Local vector DB on Hetzner for semantic search embeddings |

### Telegram Message Flow

```
Receive update (long poll)
  → Transcribe voice if needed (Whisper)
  → Router (structured output) → route + date_from? + date_to? + extra_context?
  → Intent Parser (structured output) → intent + contextual_search_term? + tags? + archived? + llm_post_process
  → Handler (CRUD / calendar API / file ops)
  → (optional) LLM post-processing pass
  → Respond: text or TTS voice note
```

### React UI Flow

```
Login screen → POST /auth → signed JWT → HttpOnly cookie
  → Chat panel: POST /message (same endpoint as Telegram pipeline)
  → Notes view: GET/POST/PATCH/DELETE /notes
  → Calendar view: GET/POST/PATCH/DELETE /calendar
  → Reminders view: GET/POST/PATCH/DELETE /reminders
```

### Router Detail

- Model: `ROUTER_LLM` (`gpt-5-nano`)
- API: Responses API with structured output (Pydantic model)
- Output fields:
  - `route`: `calendar | notes | reminders | shopping_lists | chat | help`
  - `date_from` (optional): ISO date string
  - `date_to` (optional): ISO date string
  - `extra_context` (optional): any additional context useful downstream

### Intent Parser Detail

- Model: `INTENT_PARSER` (`gpt-5-nano`)
- API: Responses API with structured output (per-route Pydantic model)
- Common output fields:
  - `intent`: `add | edit | delete | search | list`
  - `contextual_search_term` (optional): search term enriched with conversation context
  - `tags` (optional): list of tag strings
  - `archived` (optional, bool): whether to search archived items
  - `llm_post_process` (bool): whether the handler should run an LLM pass on raw results before responding
- Plus domain-specific fields per route (e.g. calendar event fields, reminder datetime)

### Data Layer

| Store | Purpose |
|---|---|
| `data/nora.db` (SQLite) | Note/shopping list metadata, tags, relationships |
| Qdrant (local) | Note embeddings for semantic search |
| `data/notes/YYMMDD-HHMM.txt` | Note content (flat files) |
| `data/shopping_lists/<date>.txt` | Shopping list content (flat files) |
| `data/reminders/reminders.json` | Reminder records |
| `data/state.json` | Conversation history + voice preference (offline analysis only) |

**SQLite schema (`data/nora.db`):**

```sql
notes(id, filepath, created_at, updated_at)
tags(id, note_id, tag)
relationships(id, note1_id, relationship, note2_id)
shopping_lists(id, filepath, created_at)
```

### Embedding Pipeline

On note save:
1. Generate embedding via OpenAI API (`EMBEDDING_MODEL`, default `text-embedding-3-small`)
2. Upsert vector into Qdrant with `note_id` as payload
3. Update `notes.updated_at` in SQLite

### Reminder Cron

System cron runs `reminders/check_reminders.py` every minute:
1. Read `data/reminders/reminders.json`
2. For each reminder that is due and not yet sent: send Telegram message via bot
3. Mark reminder as sent in `reminders.json`

## Coding Conventions

### Comments

With your comments be conservative and concise, but also helpful. Add comments to code where some operation might not be clearly obvious.

### Folder Structure

```
backend/    # Python backend (FastAPI)
frontend/   # React frontend (Vite + React 18)
data/       # Runtime data (notes, reminders, etc.)
tests/      # pytest unit tests
```

### Function Docstrings

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

### Tests

Write unit tests with pytest and store in `tests/`. Run tests on every push to GitHub.

### Linting

Use ruff for linting.

## Key Dependencies

**Backend (Python):**
- `python-telegram-bot` with job-queue
- `openai` (Responses API + Embeddings)
- `fastapi` (or Flask)
- `qdrant-client`
- `python-jose` (JWT)
- `sqlite3` (stdlib)
- `ruff` (linting)
- `pytest` (tests)

**Frontend:**
- Vite + React 18

## Key Config Variables

All stored in a config file (not hardcoded):

| Variable | Default | Description |
|---|---|---|
| `ROUTER_LLM` | `gpt-5-nano` | Model for the routing step |
| `INTENT_PARSER` | `gpt-5-nano` | Model for intent parsing |
| `HISTORY_LENGTH` | `3` | Number of conversation turns to retain |
| `PASSWORD` | — | UI login password |
| `JWT_SECRET` | — | Secret for signing session JWTs |
| `TELEGRAM_BOT_TOKEN` | — | Telegram bot token |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | — | Path to Google service account JSON |
| `QDRANT_HOST` | `localhost` | Qdrant host |
| `QDRANT_PORT` | `6333` | Qdrant port |
