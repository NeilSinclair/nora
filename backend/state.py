"""In-memory conversation history and voice preference.

History is keyed by user_id (Telegram chat_id as str, or "web" for the React UI).
It is NOT reloaded from disk on restart — state.json is append-only for offline analysis.

Voice preference IS persisted to data/preferences.json and reloaded on startup so it
survives server restarts.
"""

import asyncio
import json
from datetime import datetime, timezone

from backend.config import settings

# user_id → list of {"role": str, "content": str}
_history: dict[str, list[dict]] = {}

# Guards concurrent writes to _history from async handlers
_lock = asyncio.Lock()

# Loaded once at startup, written on every change
_voice_enabled: bool = False


def load_preferences() -> None:
    """Load persisted preferences from disk. Call once at startup."""
    global _voice_enabled
    try:
        data = json.loads(settings.preferences_file.read_text())
        _voice_enabled = bool(data.get("voice_enabled", False))
    except (FileNotFoundError, json.JSONDecodeError):
        _voice_enabled = False


def _save_preferences() -> None:
    settings.preferences_file.parent.mkdir(parents=True, exist_ok=True)
    settings.preferences_file.write_text(json.dumps({"voice_enabled": _voice_enabled}))


def get_voice_enabled() -> bool:
    return _voice_enabled


def set_voice_enabled(enabled: bool) -> None:
    global _voice_enabled
    _voice_enabled = enabled
    _save_preferences()


async def get_history(user_id: str) -> list[dict]:
    """Return the current conversation history for a user (a copy)."""
    async with _lock:
        return list(_history.get(user_id, []))


async def append_turn(user_id: str, user_text: str, assistant_text: str) -> None:
    """Append a user+assistant turn and trim to HISTORY_LENGTH turns."""
    async with _lock:
        turns = _history.setdefault(user_id, [])
        turns.append({"role": "user", "content": user_text})
        turns.append({"role": "assistant", "content": assistant_text})

        # Keep only the last HISTORY_LENGTH complete turns (2 messages per turn)
        max_messages = settings.HISTORY_LENGTH * 2
        if len(turns) > max_messages:
            _history[user_id] = turns[-max_messages:]

    _append_to_state_log(user_id, user_text, assistant_text)


def _append_to_state_log(user_id: str, user_text: str, assistant_text: str) -> None:
    """Append a turn to the append-only state.json log (offline analysis only)."""
    settings.state_file.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "user": user_text,
        "assistant": assistant_text,
    }
    with settings.state_file.open("a") as f:
        f.write(json.dumps(entry) + "\n")
