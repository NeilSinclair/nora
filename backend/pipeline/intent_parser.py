"""Intent parser stage: decodes the user's intent within a route."""

from backend.config import settings
from backend.pipeline.models import (
    BaseIntentOutput,
    CalendarIntentOutput,
    ChatIntentOutput,
    HelpIntentOutput,
    INTENT_MODEL_MAP,
    NotesIntentOutput,
    RemindersIntentOutput,
    ShoppingListsIntentOutput,
)
from backend.services.openai_client import responses_structured

# System prompts are keyed by route name
_SYSTEM_PROMPTS: dict[str, str] = {
    "notes": """
You decode the user's intent for the Notes feature.

Intent must be one of: add, edit, delete, search, list.

Also extract:
- contextual_search_term: for search intents, the enriched search term using conversation
  context (e.g. if the conversation was about IKEA and the user says "yes, but tables",
  the term is "tables at IKEA"). Null for non-search intents.
- tags: list of tag strings the user mentions. Empty list if none.
- archived: true if the user explicitly wants to search archived notes, false otherwise.
- note_id: the SQLite note ID if the user references a specific note by ID; null otherwise.
- content: the note text for add/edit intents; null otherwise.
- llm_post_process: true if the result needs further LLM processing before responding
  (e.g. summarising multiple notes, answering a question about note content).
""".strip(),

    "shopping_lists": """
You decode the user's intent for the Shopping Lists feature.

Intent must be one of: add, edit, delete, search, list.

Also extract:
- contextual_search_term: enriched search term using conversation context; null otherwise.
- archived: true if the user wants archived lists.
- list_id: the SQLite list ID if the user references a specific list; null otherwise.
- content: the shopping list text for add/edit intents; null otherwise.
- llm_post_process: true if the result needs further LLM processing (e.g. finding items
  common across multiple lists).
""".strip(),

    "reminders": """
You decode the user's intent for the Reminders feature.

Intent must be one of: add, edit, delete, list.

Also extract:
- reminder_id: the UUID of the reminder if the user references a specific one; null otherwise.
- text: the reminder message text for add/edit intents; null otherwise.
- remind_at: ISO datetime string (YYYY-MM-DDTHH:MM:SS) for when the reminder should fire.
  Resolve relative times using the current date provided in the conversation. Null if not
  mentioned.
- llm_post_process: almost always false for reminders.
""".strip(),

    "calendar": """
You decode the user's intent for the Calendar feature.

Intent must be one of: add, edit, delete, search, list.

Also extract:
- event_id: the Google Calendar event ID if the user references a specific event; null otherwise.
- title: event title for add/edit intents; null otherwise.
- start: ISO datetime string (YYYY-MM-DDTHH:MM:SS) for event start; null if not mentioned.
- end: ISO datetime string for event end; null if not mentioned.
- description: optional event description text; null if not mentioned.
- contextual_search_term: for search intents, enriched search term; null otherwise.
- llm_post_process: true if the user asks a question about calendar contents rather than
  just wanting to see raw events.
""".strip(),

    "chat": """
The user is having a free-form conversation. Set intent to "chat" and llm_post_process to true.
""".strip(),

    "help": """
The user wants to know what Nora can do. Set intent to "list" and llm_post_process to false.
""".strip(),
}


async def parse_intent(
    route: str,
    raw_text: str,
    history: list[dict],
    router_extra_context: str | None = None,
) -> BaseIntentOutput:
    """Parse the user's intent within the given route.

    Args:
      route (str): The route determined by the router stage.
      raw_text (str): The user's current message.
      history (list[dict]): Recent conversation turns for context.
      router_extra_context (str | None): Extra context captured by the router.

    Returns:
      BaseIntentOutput: Structured intent for the handler.
    """
    output_model = INTENT_MODEL_MAP[route]
    system_prompt = _SYSTEM_PROMPTS[route]

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)

    user_content = raw_text
    if router_extra_context:
        user_content = f"{raw_text}\n\n[Context: {router_extra_context}]"
    messages.append({"role": "user", "content": user_content})

    return await responses_structured(
        model=settings.INTENT_PARSER,
        messages=messages,
        output_model=output_model,
        temperature=0.0,
    )
