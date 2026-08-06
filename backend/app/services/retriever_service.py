"""Turns a natural-language query into the top-K most relevant repository chunks.

Pure retrieval: embeds the query with whatever provider is configured (must match
the provider that produced the repository's stored vectors), searches Qdrant, and
returns structured results. Building an LLM prompt from these results is
app.services.prompt_service; calling the LLM itself is app.services.chat_service
(Milestone 10). Deliberately takes a plain collection_name rather than a Repository
ORM object so it stays testable without any DB/model coupling.
"""
from dataclasses import dataclass

from app.ai.vector_store.qdrant_client import search
from app.core.config import settings
from app.services.embedding_service import get_embedding_provider


@dataclass
class RetrievedChunk:
    file_path: str
    language: str | None
    content: str
    start_line: int | None
    end_line: int | None
    chunk_index: int
    score: float


async def retrieve_relevant_chunks(
    collection_name: str,
    query: str,
    top_k: int | None = None,
    score_threshold: float | None = None,
) -> list[RetrievedChunk]:
    """Embeds `query` and returns the top-K most similar chunks from `collection_name`."""
    if not query or not query.strip():
        return []

    provider = get_embedding_provider()
    query_vector = await provider.embed_query(query)

    scored_points = await search(
        collection_name,
        query_vector=query_vector,
        top_k=top_k or settings.RETRIEVAL_TOP_K,
        score_threshold=score_threshold if score_threshold is not None else settings.RETRIEVAL_SCORE_THRESHOLD,
    )

    chunks: list[RetrievedChunk] = []
    for point in scored_points:
        payload = point.payload or {}
        content = payload.get("content")
        if not content:
            # A point with no stored content is useless as LLM context — skip it
            # rather than surface an empty/misleading "unknown" source.
            continue
        chunks.append(
            RetrievedChunk(
                file_path=payload.get("file_path", "unknown"),
                language=payload.get("language"),
                content=content,
                start_line=payload.get("start_line"),
                end_line=payload.get("end_line"),
                chunk_index=payload.get("chunk_index", 0),
                score=point.score,
            )
        )
    return chunks
