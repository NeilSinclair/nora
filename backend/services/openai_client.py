"""Singleton OpenAI client with helpers for the Responses API and Embeddings."""

import json
from typing import Any, Type, TypeVar

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
    """Call the Responses API and parse the output into a Pydantic model.

    Args:
      model (str): OpenAI model ID.
      messages (list[dict]): List of {"role": ..., "content": ...} dicts.
      output_model (Type[T]): Pydantic model class to parse the JSON response into.
      temperature (float): Sampling temperature.

    Returns:
      T: Parsed Pydantic model instance.
    """
    schema = output_model.model_json_schema()
    response = await get_client().responses.create(
        model=model,
        input=messages,
        temperature=temperature,
        text={
            "format": {
                "type": "json_schema",
                "json_schema": {
                    "name": output_model.__name__,
                    "schema": schema,
                    "strict": True,
                },
            }
        },
    )
    return output_model.model_validate_json(response.output_text)


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
