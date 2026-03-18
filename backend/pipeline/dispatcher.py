"""Dispatcher: routes a PipelineContext to the correct handler."""

import logging
import time

from backend.config import settings
from backend.pipeline.models import PipelineContext
from backend.services.openai_client import responses_text

logger = logging.getLogger(__name__)

_LLM_POST_PROCESS_SYSTEM_PROMPT = """
You are Nora, a friendly and concise AI assistant.
The following is raw data retrieved for the user. Process it to give a helpful,
natural-language response to what the user asked. Be brief and direct.
""".strip()


async def dispatch(ctx: PipelineContext) -> str:
    """Call the appropriate handler and optionally apply an LLM post-processing pass.

    Args:
      ctx (PipelineContext): Fully populated pipeline context (route + intent filled in).

    Returns:
      str: Final response text to send back to the user.
    """
    t0 = time.perf_counter()
    raw_result = await _call_handler(ctx)
    logger.info("[HANDLER:%s] completed in %.2fs result=%r", ctx.route,
                time.perf_counter() - t0, raw_result[:80])

    if ctx.intent_data and ctx.intent_data.llm_post_process:
        logger.info("[LLM_POST_PROCESS] running...")
        t1 = time.perf_counter()
        result = await _llm_post_process(ctx.raw_text, raw_result, ctx.history)
        logger.info("[LLM_POST_PROCESS] completed in %.2fs", time.perf_counter() - t1)
        return result

    return raw_result


async def _call_handler(ctx: PipelineContext) -> str:
    # Import handlers here to avoid circular imports at module load time
    match ctx.route:
        case "notes":
            from backend.handlers.notes import handle as notes_handle
            return await notes_handle(ctx)
        case "shopping_lists":
            from backend.handlers.shopping_lists import handle as shopping_handle
            return await shopping_handle(ctx)
        case "reminders":
            from backend.handlers.reminders import handle as reminders_handle
            return await reminders_handle(ctx)
        case "calendar":
            from backend.handlers.calendar import handle as calendar_handle
            return await calendar_handle(ctx)
        case "chat":
            from backend.handlers.chat import handle as chat_handle
            return await chat_handle(ctx)
        case "help":
            from backend.handlers.help import handle as help_handle
            return await help_handle(ctx)
        case _:
            return "Sorry, I didn't understand that. Try asking for /help."


async def _llm_post_process(user_text: str, raw_data: str, history: list[dict]) -> str:
    """Run an LLM pass on raw handler output before returning to the user.

    Args:
      user_text (str): The original user message.
      raw_data (str): Raw data returned by the handler.
      history (list[dict]): Conversation history for context.

    Returns:
      str: LLM-processed response.
    """
    messages = [{"role": "system", "content": _LLM_POST_PROCESS_SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_text})
    messages.append({"role": "assistant", "content": f"[Raw data]\n{raw_data}"})
    messages.append({"role": "user", "content": "Please give me a natural response based on the above."})

    return await responses_text(
        model=settings.ROUTER_LLM,
        messages=messages,
        temperature=0.7,
    )
