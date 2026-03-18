"""Single-call pipeline: replaces the sequential router + intent parser with one LLM call."""

import logging

from backend.config import settings
from backend.pipeline.models import (
    BaseIntentOutput,
    CalendarIntentOutput,
    CombinedOutput,
    NotesIntentOutput,
    RemindersIntentOutput,
    ShoppingListsIntentOutput,
    ChatIntentOutput,
    HelpIntentOutput,
    PipelineContext,
)
from backend.services.openai_client import responses_structured

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """
You are the brain of Nora, an AI assistant. Given a user message, output a single JSON
object that captures both the routing decision AND the full intent in one step.

## Route
Choose exactly one:
  calendar, notes, reminders, shopping_lists, chat, help

## Intent
Choose exactly one based on the route:
  add, edit, delete, search, list, chat

- Use "chat" only for the route "chat".
- Use "list" for the route "help".

## Fields to populate (only fill what applies)

**All routes:**
- date_from / date_to: ISO date (YYYY-MM-DD) if the user mentions dates; otherwise null.
- extra_context: brief extra context useful downstream; null if none.
- llm_post_process: true if the raw result needs LLM summarisation before responding
  (e.g. "what do these notes have in common?", free-form chat, calendar questions).
  Always true for route=chat.

**notes / shopping_lists:**
- contextual_search_term: for search, the enriched term using conversation context.
- tags: list of tags mentioned; empty list if none.
- archived: true if user wants archived items.
- content: the text to add/edit; null otherwise.
- note_id: SQLite note ID if user references a specific note; null otherwise.
- list_id: SQLite list ID if user references a specific list; null otherwise.

**reminders:**
- reminder_id: UUID if user references a specific reminder; null otherwise.
- reminder_text: the reminder message for add/edit; null otherwise.
- remind_at: ISO datetime (YYYY-MM-DDTHH:MM:SS) for when to fire; null if not mentioned.

**calendar:**
- event_id: Google Calendar event ID if user references a specific event; null otherwise.
- title: event title for add/edit; null otherwise.
- start / end: ISO datetime for event times; null if not mentioned.
- event_description: event description text; null if not mentioned.

Respond with ONLY a valid JSON object — no markdown, no explanation, no code fences.
Only populate fields relevant to the route; use null for everything else.
""".strip()


async def run_pipeline(text: str, history: list[dict]) -> CombinedOutput:
    """Run routing and intent parsing in a single LLM call.

    Args:
      text (str): The user's message.
      history (list[dict]): Recent conversation turns.

    Returns:
      CombinedOutput: Routing + intent in one structured object.
    """
    messages = [{"role": "system", "content": _SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": text})

    return await responses_structured(
        model=settings.ROUTER_LLM,
        messages=messages,
        output_model=CombinedOutput,
        temperature=0.0,
    )


def to_intent_data(output: CombinedOutput) -> BaseIntentOutput:
    """Convert a CombinedOutput into the appropriate intent data object for the handler.

    Args:
      output (CombinedOutput): The combined pipeline output.

    Returns:
      BaseIntentOutput: The route-specific intent object the handler expects.
    """
    match output.route:
        case "notes":
            return NotesIntentOutput(
                intent=output.intent,  # type: ignore[arg-type]
                llm_post_process=output.llm_post_process,
                contextual_search_term=output.contextual_search_term,
                tags=output.tags,
                archived=output.archived,
                content=output.content,
                note_id=output.note_id,
            )
        case "shopping_lists":
            return ShoppingListsIntentOutput(
                intent=output.intent,  # type: ignore[arg-type]
                llm_post_process=output.llm_post_process,
                contextual_search_term=output.contextual_search_term,
                archived=output.archived,
                content=output.content,
                list_id=output.list_id,
            )
        case "reminders":
            return RemindersIntentOutput(
                intent=output.intent,  # type: ignore[arg-type]
                llm_post_process=output.llm_post_process,
                reminder_id=output.reminder_id,
                text=output.reminder_text,
                remind_at=output.remind_at,
            )
        case "calendar":
            return CalendarIntentOutput(
                intent=output.intent,  # type: ignore[arg-type]
                llm_post_process=output.llm_post_process,
                event_id=output.event_id,
                title=output.title,
                start=output.start,
                end=output.end,
                description=output.event_description,
                contextual_search_term=output.contextual_search_term,
            )
        case "chat":
            return ChatIntentOutput(llm_post_process=True)
        case "help":
            return HelpIntentOutput(intent="list")
        case _:
            return ChatIntentOutput(llm_post_process=True)
