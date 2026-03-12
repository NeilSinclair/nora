"""Voice transcription via OpenAI Whisper."""

from backend.services.openai_client import get_client


async def transcribe(audio_bytes: bytes, filename: str = "audio.ogg") -> str:
    """Transcribe audio bytes to text using Whisper.

    Args:
      audio_bytes (bytes): Raw audio data (ogg, mp4, wav, etc.).
      filename (str): Filename hint used by the API to detect format.

    Returns:
      str: Transcribed text.
    """
    client = get_client()
    # The API expects a file-like object; wrap bytes in a tuple (name, bytes, mime)
    response = await client.audio.transcriptions.create(
        model="whisper-1",
        file=(filename, audio_bytes, "audio/ogg"),
    )
    return response.text
