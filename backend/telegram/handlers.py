"""Telegram update handlers: text and voice messages."""

import logging
import time

from telegram import Update
from telegram.ext import ContextTypes

from backend.pipeline.dispatcher import dispatch
from backend.pipeline.intent_parser import parse_intent
from backend.pipeline.models import PipelineContext
from backend.pipeline.router import route
from backend.services.tts import synthesise
from backend.services.whisper import transcribe
from backend import state

logger = logging.getLogger(__name__)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle an incoming text message."""
    user_id = str(update.effective_chat.id)
    text = update.message.text.strip()
    logger.info("[IN] user=%s text=%r", user_id, text)

    lower = text.lower()
    if any(phrase in lower for phrase in ("voice on", "speak to me", "voice responses on")):
        state.set_voice_enabled(True)
        await update.message.reply_text("Voice responses enabled.")
        return
    if any(phrase in lower for phrase in ("voice off", "stop speaking", "voice responses off")):
        state.set_voice_enabled(False)
        await update.message.reply_text("Voice responses disabled.")
        return

    response_text = await _run_pipeline(user_id, text)
    await _send_response(update, response_text)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle an incoming voice message: give immediate feedback, transcribe, then pipeline."""
    user_id = str(update.effective_chat.id)
    logger.info("[IN] user=%s voice message received", user_id)

    await update.message.reply_text("🎙 Transcribing...")

    t0 = time.perf_counter()
    voice_file = await update.message.voice.get_file()
    audio_bytes = await voice_file.download_as_bytearray()
    text = await transcribe(bytes(audio_bytes), filename="voice.ogg")
    logger.info("[WHISPER] transcribed in %.2fs text=%r", time.perf_counter() - t0, text)

    await update.message.reply_text(f"📝 _{text}_", parse_mode="Markdown")

    response_text = await _run_pipeline(user_id, text)
    await _send_response(update, response_text)


async def _run_pipeline(user_id: str, text: str) -> str:
    history = await state.get_history(user_id)
    logger.info("[PIPELINE] starting | user=%s | history_turns=%d", user_id, len(history) // 2)

    t0 = time.perf_counter()
    logger.info("[ROUTER] calling model...")
    router_output = await route(text, history)
    logger.info("[ROUTER] completed in %.2fs route=%s date_from=%s date_to=%s",
                time.perf_counter() - t0, router_output.route,
                router_output.date_from, router_output.date_to)

    t1 = time.perf_counter()
    logger.info("[INTENT] calling model for route=%s...", router_output.route)
    intent_data = await parse_intent(
        route=router_output.route,
        raw_text=text,
        history=history,
        router_extra_context=router_output.extra_context,
    )
    logger.info("[INTENT] completed in %.2fs intent=%s llm_post_process=%s data=%s",
                time.perf_counter() - t1, intent_data.intent,
                intent_data.llm_post_process, intent_data.model_dump(exclude_none=True))

    ctx = PipelineContext(
        user_id=user_id,
        raw_text=text,
        history=history,
        route=router_output.route,
        date_from=router_output.date_from,
        date_to=router_output.date_to,
        extra_context=router_output.extra_context,
        intent=intent_data.intent,
        intent_data=intent_data,
    )

    t2 = time.perf_counter()
    logger.info("[DISPATCH] → handler=%s", ctx.route)
    response_text = await dispatch(ctx)
    logger.info("[DISPATCH] ← completed in %.2fs response=%r",
                time.perf_counter() - t2, response_text[:120])

    await state.append_turn(user_id, text, response_text)
    logger.info("[OUT] total=%.2fs sending response to user=%s",
                time.perf_counter() - t0, user_id)
    return response_text


async def _send_response(update: Update, text: str) -> None:
    if state.get_voice_enabled():
        logger.info("[TTS] synthesising voice response...")
        t0 = time.perf_counter()
        audio = await synthesise(text)
        logger.info("[TTS] completed in %.2fs", time.perf_counter() - t0)
        await update.message.reply_voice(voice=audio)
    else:
        await update.message.reply_text(text)
