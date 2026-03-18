"""Singleton OpenAI client with helpers for the Responses API and Embeddings."""

from typing import Type, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel

from backend.config import settings

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


T = TypeVar("T", bound=BaseModel)


async def responses_structured(
    model: str,
    messages: list[dict],
    output_model: Type[T],
    temperature: float = 0.0,
) -> T:
    """Call the Responses API and parse the JSON text output into a Pydantic model.

    Uses plain text output rather than constrained decoding — avoids the latency
    overhead of structured outputs while still getting reliable JSON from the model.

    Args:
      model (str): OpenAI model ID.
      messages (list[dict]): List of {"role": ..., "content": ...} dicts.
      output_model (Type[T]): Pydantic model class to parse the response into.
      temperature (float): Sampling temperature.

    Returns:
      T: Parsed Pydantic model instance.
    """
    response = await get_client().responses.parse(
        model=model,
        input=messages,
        text_format=output_model,
    )
    return response.output_parsed


async def responses_text(
    model: str,
    messages: list[dict],
    temperature: float = 0.7,
) -> str:
    """Call the Responses API and return the raw text response.

    Args:
      model (str): OpenAI model ID.
      messages (list[dict]): List of {"role": ..., "content": ...} dicts.
      temperature (float): Sampling temperature.

    Returns:
      str: The model's text response.
    """
    response = await get_client().responses.create(
        model=model,
        input=messages,
        temperature=temperature,
    )
    return response.output_text


async def get_embedding(text: str) -> list[float]:
    """Generate an embedding for text using the configured embedding model.

    Args:
      text (str): The text to embed.

    Returns:
      list[float]: Embedding vector.
    """
    response = await get_client().embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding
