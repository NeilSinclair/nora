import sqlite3
from contextlib import contextmanager
from typing import Generator

from backend.config import settings

_CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS notes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    filepath    TEXT    NOT NULL UNIQUE,
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS tags (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id  INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    tag      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS relationships (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    note1_id     INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    relationship TEXT    NOT NULL,
    note2_id     INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS shopping_lists (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    filepath   TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);
"""


def init_db() -> None:
    """Create all tables if they don't exist. Safe to call multiple times."""
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(settings.db_path) as conn:
        conn.executescript(_CREATE_TABLES)
        conn.execute("PRAGMA foreign_keys = ON")


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Yield an open SQLite connection with foreign keys enabled and Row factory set."""
    conn = sqlite3.connect(settings.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
