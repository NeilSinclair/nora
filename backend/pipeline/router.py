"""Router stage: classifies the user's message into a route."""

from backend.config import settings
from backend.pipeline.models import RouterOutput
from backend.services.openai_client import responses_structured

ROUTER_SYSTEM_PROMPT = """
You classify user messages into exactly one of the following routes:
  calendar, notes, reminders, shopping_lists, chat, help

Rules:
- Choose the single best-fitting route based on the user's primary intent.
- If the message could fit multiple routes, prefer the more specific one.
- Use "chat" only when no other route applies.
- Use "help" when the user asks what Nora can do or asks for instructions.

Also extract:
- date_from: an ISO date string (YYYY-MM-DD) if the user mentions a start date or a single
  date reference (e.g. "tomorrow", "next Monday"); otherwise null.
- date_to: an ISO date string if the user mentions an end date or range; otherwise null.
  Resolve relative dates using the current date provided in the conversation.
- extra_context: any additional information (entities, subjects, names) that would help
  downstream processing. Keep it brief. Null if nothing notable.

Output valid JSON matching the schema exactly.
""".strip()


async def route(raw_text: str, history: list[dict]) -> RouterOutput:
    """Classify the user's message into a route.

    Args:
      raw_text (str): The user's current message.
      history (list[dict]): Recent conversation turns for context.

    Returns:
      RouterOutput: Structured routing decision.
    """
    messages = [{"role": "system", "content": ROUTER_SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": raw_text})

    return await responses_structured(
        model=settings.ROUTER_LLM,
        messages=messages,
        output_model=RouterOutput,
        temperature=0.0,
    )
