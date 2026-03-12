"""Singleton Qdrant client with helpers for note embedding storage and search."""

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

from backend.config import settings

# text-embedding-3-small produces 1536-dimensional vectors
_EMBEDDING_DIM = 1536
_COLLECTION = "notes"

_client: AsyncQdrantClient | None = None


def get_client() -> AsyncQdrantClient:
    global _client
    if _client is None:
        _client = AsyncQdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
    return _client


async def ensure_collection() -> None:
    """Create the notes collection if it doesn't already exist. Call once at startup."""
    client = get_client()
    existing = await client.get_collections()
    names = [c.name for c in existing.collections]
    if _COLLECTION not in names:
        await client.create_collection(
            collection_name=_COLLECTION,
            vectors_config=VectorParams(size=_EMBEDDING_DIM, distance=Distance.COSINE),
        )


async def upsert_note(note_id: int, embedding: list[float], filepath: str) -> None:
    """Insert or update a note's embedding in Qdrant.

    Args:
      note_id (int): SQLite note ID used as the Qdrant point ID.
      embedding (list[float]): 1536-dim embedding vector.
      filepath (str): Note filepath stored as payload for reference.
    """
    await get_client().upsert(
        collection_name=_COLLECTION,
        points=[PointStruct(id=note_id, vector=embedding, payload={"filepath": filepath})],
    )


async def search_notes(embedding: list[float], limit: int = 10) -> list[dict]:
    """Search for semantically similar notes.

    Args:
      embedding (list[float]): Query embedding vector.
      limit (int): Maximum number of results to return.

    Returns:
      list[dict]: List of {"note_id": int, "filepath": str, "score": float} dicts.
    """
    results = await get_client().search(
        collection_name=_COLLECTION,
        query_vector=embedding,
        limit=limit,
        with_payload=True,
    )
    return [
        {"note_id": r.id, "filepath": r.payload["filepath"], "score": r.score}
        for r in results
    ]


async def delete_note(note_id: int) -> None:
    """Remove a note's embedding from Qdrant.

    Args:
      note_id (int): SQLite note ID.
    """
    from qdrant_client.models import PointIdsList

    await get_client().delete(
        collection_name=_COLLECTION,
        points_selector=PointIdsList(points=[note_id]),
    )
