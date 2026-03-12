"""Text-to-speech synthesis via OpenAI TTS."""

from backend.services.openai_client import get_client

# Voice used for all TTS responses
_VOICE = "alloy"


async def synthesise(text: str) -> bytes:
    """Convert text to speech and return raw MP3 bytes.

    Args:
      text (str): Text to synthesise.

    Returns:
      bytes: MP3 audio data.
    """
    client = get_client()
    response = await client.audio.speech.create(
        model="tts-1",
        voice=_VOICE,
        input=text,
        response_format="mp3",
    )
    return response.content
