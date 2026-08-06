"""Async Qdrant client wrapper: collection lifecycle, upsert, and vector search.

Everything here is generic vector-store capability — no RAG-specific logic (prompt
building, context assembly) lives in this module. That's app.services.retriever_service
(Milestone 9), which calls search() and turns results into LLM context.
"""
from functools import lru_cache

from qdrant_client import AsyncQdrantClient, models

from app.core.config import settings
from app.core.exceptions import ExternalServiceException
from app.core.logging import get_logger

logger = get_logger(__name__)


@lru_cache
def get_qdrant_client() -> AsyncQdrantClient:
    return AsyncQdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)


async def ensure_collection(collection_name: str, vector_size: int) -> None:
    """Creates the collection if it doesn't already exist. Idempotent."""
    client = get_qdrant_client()
    try:
        if not await client.collection_exists(collection_name):
            await client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
            )
            logger.info("Created Qdrant collection %s (size=%s)", collection_name, vector_size)
    except Exception as exc:
        raise ExternalServiceException(f"Failed to ensure Qdrant collection {collection_name}: {exc}") from exc


async def upsert_chunks(collection_name: str, points: list[tuple[str, list[float], dict]]) -> None:
    """points: list of (point_id, vector, payload) triples."""
    if not points:
        return

    client = get_qdrant_client()
    try:
        await client.upsert(
            collection_name=collection_name,
            points=[
                models.PointStruct(id=point_id, vector=vector, payload=payload)
                for point_id, vector, payload in points
            ],
        )
    except Exception as exc:
        raise ExternalServiceException(
            f"Failed to upsert into Qdrant collection {collection_name}: {exc}"
        ) from exc


async def search(
    collection_name: str,
    query_vector: list[float],
    top_k: int = 5,
    score_threshold: float | None = None,
) -> list[models.ScoredPoint]:
    client = get_qdrant_client()
    try:
        response = await client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=top_k,
            score_threshold=score_threshold,
            with_payload=True,
        )
        return response.points
    except Exception as exc:
        raise ExternalServiceException(f"Failed to search Qdrant collection {collection_name}: {exc}") from exc


async def delete_collection(collection_name: str) -> None:
    client = get_qdrant_client()
    try:
        if await client.collection_exists(collection_name):
            await client.delete_collection(collection_name)
    except Exception as exc:
        # Best-effort cleanup — a dangling Qdrant collection after a repository is
        # deleted is wasted storage, not a correctness problem, so we log and move on
        # rather than fail the (already-committed) DB deletion.
        logger.warning("Failed to delete Qdrant collection %s: %s", collection_name, exc)
