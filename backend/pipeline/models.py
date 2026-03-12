"""Pydantic models for pipeline structured outputs and the central PipelineContext."""

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Router output
# ---------------------------------------------------------------------------

Route = Literal["calendar", "notes", "reminders", "shopping_lists", "chat", "help"]


class RouterOutput(BaseModel):
    route: Route
    date_from: str | None = None  # ISO date string
    date_to: str | None = None    # ISO date string
    extra_context: str | None = None


# ---------------------------------------------------------------------------
# Intent outputs — one per route
# ---------------------------------------------------------------------------

Intent = Literal["add", "edit", "delete", "search", "list"]


class BaseIntentOutput(BaseModel):
    intent: Intent
    llm_post_process: bool = False


class NotesIntentOutput(BaseIntentOutput):
    contextual_search_term: str | None = None
    tags: list[str] = []
    archived: bool = False
    note_id: int | None = None         # for edit/delete
    content: str | None = None         # for add/edit
    relationship: str | None = None    # for linking; used in UI only


class ShoppingListsIntentOutput(BaseIntentOutput):
    contextual_search_term: str | None = None
    archived: bool = False
    list_id: int | None = None
    content: str | None = None


class RemindersIntentOutput(BaseIntentOutput):
    reminder_id: str | None = None
    text: str | None = None
    remind_at: str | None = None  # ISO datetime string


class CalendarIntentOutput(BaseIntentOutput):
    event_id: str | None = None
    title: str | None = None
    start: str | None = None   # ISO datetime string
    end: str | None = None     # ISO datetime string
    description: str | None = None
    contextual_search_term: str | None = None


class ChatIntentOutput(BaseIntentOutput):
    intent: Literal["chat"] = "chat"  # type: ignore[assignment]
    llm_post_process: bool = True


class HelpIntentOutput(BaseIntentOutput):
    intent: Literal["list"] = "list"  # type: ignore[assignment]


# Map from route string to the intent model class
INTENT_MODEL_MAP: dict[str, type[BaseIntentOutput]] = {
    "notes": NotesIntentOutput,
    "shopping_lists": ShoppingListsIntentOutput,
    "reminders": RemindersIntentOutput,
    "calendar": CalendarIntentOutput,
    "chat": ChatIntentOutput,
    "help": HelpIntentOutput,
}


# ---------------------------------------------------------------------------
# Pipeline context — carries all data through the pipeline
# ---------------------------------------------------------------------------

@dataclass
class PipelineContext:
    user_id: str
    raw_text: str
    history: list[dict] = field(default_factory=list)

    # Filled by router
    route: str = ""
    date_from: str | None = None
    date_to: str | None = None
    extra_context: str | None = None

    # Filled by intent parser
    intent: str = ""
    intent_data: BaseIntentOutput | None = None

    # Filled by handler / dispatcher
    response_text: str | None = None
