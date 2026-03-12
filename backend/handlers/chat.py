"""Free-form chat handler: passes the conversation to the LLM directly."""

from backend.config import settings
from backend.pipeline.models import PipelineContext
from backend.services.openai_client import responses_text

_CHAT_SYSTEM_PROMPT = """
You are Nora, a friendly and concise AI assistant. Answer the user's questions helpfully.
Keep responses brief and to the point unless detail is clearly needed.
""".strip()


async def handle(ctx: PipelineContext) -> str:
    """Pass the conversation to the LLM and return its response.

    Args:
      ctx (PipelineContext): Pipeline context with history and raw_text.

    Returns:
      str: The LLM's response.
    """
    messages = [{"role": "system", "content": _CHAT_SYSTEM_PROMPT}]
    messages.extend(ctx.history)
    messages.append({"role": "user", "content": ctx.raw_text})

    return await responses_text(
        model=settings.ROUTER_LLM,
        messages=messages,
        temperature=0.7,
    )
