"""Voice endpoints: transcription and synthesis for the web UI."""

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response

from backend.api.deps import require_auth
from backend.services.tts import synthesise
from backend.services.whisper import transcribe

router = APIRouter(prefix="/voice", dependencies=[Depends(require_auth)])


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """Transcribe an uploaded audio file to text.

    Returns:
      JSON with "text" field containing the transcription.
    """
    audio_bytes = await file.read()
    text = await transcribe(audio_bytes, filename=file.filename or "audio.ogg")
    return {"text": text}


@router.post("/synthesise")
async def synthesise_speech(text: str):
    """Convert text to speech and return MP3 audio.

    Args:
      text (str): Text to synthesise (passed as query parameter).

    Returns:
      MP3 audio bytes.
    """
    audio = await synthesise(text)
    return Response(content=audio, media_type="audio/mpeg")
