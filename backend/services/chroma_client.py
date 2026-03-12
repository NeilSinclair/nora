"""ChromaDB client for local persistent vector storage.

ChromaDB runs embedded — no server or Docker required. Data is persisted to CHROMA_PATH.
"""

import asyncio

import chromadb
from chromadb.config import Settings as ChromaSettings

from backend.config import settings

_COLLECTION_NAME = "notes"

_client: chromadb.PersistentClient | None = None
_collection: chromadb.Collection | None = None


def _get_collection() -> chromadb.Collection:
    global _client, _collection
    if _collection is None:
        settings.CHROMA_PATH.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=str(settings.CHROMA_PATH),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        _collection = _client.get_or_create_collection(
            name=_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def init_chroma() -> None:
    """Initialise the ChromaDB collection. Call once at startup."""
    _get_collection()


async def upsert_note(note_id: int, embedding: list[float], filepath: str) -> None:
    """Insert or update a note's embedding.

    Args:
      note_id (int): SQLite note ID (used as the Chroma document ID).
      embedding (list[float]): Embedding vector.
      filepath (str): Note filepath stored as metadata.
    """
    collection = _get_collection()
    await asyncio.to_thread(
        collection.upsert,
        ids=[str(note_id)],
        embeddings=[embedding],
        metadatas=[{"filepath": filepath}],
    )


async def search_notes(embedding: list[float], limit: int = 10) -> list[dict]:
    """Search for semantically similar notes.

    Args:
      embedding (list[float]): Query embedding vector.
      limit (int): Maximum number of results to return.

    Returns:
      list[dict]: List of {"note_id": int, "filepath": str, "score": float} dicts.
    """
    collection = _get_collection()
    results = await asyncio.to_thread(
        collection.query,
        query_embeddings=[embedding],
        n_results=min(limit, collection.count() or 1),
        include=["metadatas", "distances"],
    )
    output = []
    ids = results["ids"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]
    for doc_id, meta, dist in zip(ids, metadatas, distances):
        # Chroma cosine distance is 1 - similarity; convert to a similarity score
        output.append({
            "note_id": int(doc_id),
            "filepath": meta["filepath"],
            "score": round(1 - dist, 4),
        })
    return output


async def delete_note(note_id: int) -> None:
    """Remove a note's embedding.

    Args:
      note_id (int): SQLite note ID.
    """
    collection = _get_collection()
    await asyncio.to_thread(collection.delete, ids=[str(note_id)])
