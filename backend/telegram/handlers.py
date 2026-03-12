"""Telegram update handlers: text and voice messages."""

from telegram import Update
from telegram.ext import ContextTypes

from backend.pipeline.dispatcher import dispatch
from backend.pipeline.intent_parser import parse_intent
from backend.pipeline.models import PipelineContext
from backend.pipeline.router import route
from backend.services.tts import synthesise
from backend.services.whisper import transcribe
from backend import state


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle an incoming text message."""
    user_id = str(update.effective_chat.id)
    text = update.message.text.strip()

    # Allow the user to toggle voice responses inline
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
    """Handle an incoming voice message: transcribe then run through pipeline."""
    user_id = str(update.effective_chat.id)
    voice_file = await update.message.voice.get_file()
    audio_bytes = await voice_file.download_as_bytearray()
    text = await transcribe(bytes(audio_bytes), filename="voice.ogg")
    response_text = await _run_pipeline(user_id, text)
    await _send_response(update, response_text)


async def _run_pipeline(user_id: str, text: str) -> str:
    history = await state.get_history(user_id)
    router_output = await route(text, history)

    ctx = PipelineContext(
        user_id=user_id,
        raw_text=text,
        history=history,
        route=router_output.route,
        date_from=router_output.date_from,
        date_to=router_output.date_to,
        extra_context=router_output.extra_context,
    )
    ctx.intent_data = await parse_intent(
        route=ctx.route,
        raw_text=ctx.raw_text,
        history=ctx.history,
        router_extra_context=ctx.extra_context,
    )
    ctx.intent = ctx.intent_data.intent

    response_text = await dispatch(ctx)
    await state.append_turn(user_id, text, response_text)
    return response_text


async def _send_response(update: Update, text: str) -> None:
    if state.get_voice_enabled():
        audio = await synthesise(text)
        await update.message.reply_voice(voice=audio)
    else:
        await update.message.reply_text(text)
