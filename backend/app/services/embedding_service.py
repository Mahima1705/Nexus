"""Selects the configured embedding provider and drives chunk -> embed -> store -> persist.

Each file goes through one atomic pipeline step: chunk (Milestone 6) -> embed
(this milestone's provider) -> upsert into Qdrant -> write the matching
EmbeddingMetadata row in Postgres. `index_repository_file` also returns the
(chunk, vector, point_id) triples it computed, in case a caller wants them
without a second embedding pass (e.g. a future re-index-without-re-embed path).
"""
import uuid
from functools import lru_cache
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings.base import EmbeddingProvider
from app.ai.vector_store.qdrant_client import ensure_collection, upsert_chunks
from app.core.config import settings
from app.core.exceptions import BadRequestException
from app.core.logging import get_logger
from app.models.embedding_metadata import EmbeddingMetadata
from app.models.repository import Repository
from app.models.repository_file import RepositoryFile
from app.repository_processor.chunker import CodeChunk, chunk_repository_file
from app.repository_processor.file_filter import is_binary_extension

logger = get_logger(__name__)


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    if settings.EMBEDDING_PROVIDER == "openai":
        from app.ai.embeddings.openai_embeddings import OpenAIEmbeddingProvider

        return OpenAIEmbeddingProvider()
    if settings.EMBEDDING_PROVIDER == "bge":
        from app.ai.embeddings.bge_embeddings import BGEEmbeddingProvider

        return BGEEmbeddingProvider()
    raise BadRequestException(f"Unsupported embedding provider: {settings.EMBEDDING_PROVIDER}")


async def index_repository_file(
    db: AsyncSession,
    repository: Repository,
    repository_file: RepositoryFile,
    repo_root: Path,
) -> list[tuple[CodeChunk, list[float], str]]:
    """Chunks, embeds, and stores one file's vectors in Qdrant, persisting an
    EmbeddingMetadata row per chunk.

    Binary files and files skipped for size in Milestone 5's file walk are left
    un-indexed (is_indexed stays False) rather than sent through the chunker.
    """
    if is_binary_extension(Path(repository_file.file_path)) or repository_file.content_hash.startswith(
        "skipped:"
    ):
        return []

    absolute_path = repo_root / repository_file.file_path
    chunks = chunk_repository_file(absolute_path, Path(repository_file.file_path), repository_file.language)

    if not chunks:
        repository_file.is_indexed = True
        await db.commit()
        return []

    provider = get_embedding_provider()
    vectors = await provider.embed_texts([chunk.content for chunk in chunks])

    await ensure_collection(repository.qdrant_collection_name, provider.dimensions)

    results: list[tuple[CodeChunk, list[float], str]] = []
    points: list[tuple[str, list[float], dict]] = []
    for chunk, vector in zip(chunks, vectors):
        # Canonical dashed form: Qdrant normalizes point IDs internally and returns
        # them dashed from search(), so storing anything else here would make
        # EmbeddingMetadata.qdrant_point_id silently fail to match search results.
        point_id = str(uuid.uuid4())
        db.add(
            EmbeddingMetadata(
                repository_id=repository.id,
                file_id=repository_file.id,
                qdrant_point_id=point_id,
                chunk_index=chunk.chunk_index,
                file_path=chunk.file_path,
                language=chunk.language,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                token_count=chunk.token_count,
            )
        )
        payload = {
            "repository_id": str(repository.id),
            "file_id": str(repository_file.id),
            "file_path": chunk.file_path,
            "language": chunk.language,
            "chunk_index": chunk.chunk_index,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
            "content": chunk.content,
        }
        points.append((point_id, vector, payload))
        results.append((chunk, vector, point_id))

    await upsert_chunks(repository.qdrant_collection_name, points)

    repository_file.is_indexed = True
    repository.total_chunks += len(chunks)
    await db.commit()

    logger.info(
        "Embedded and stored %s chunks for %s in repository %s",
        len(results),
        repository_file.file_path,
        repository.id,
    )
    return results


async def index_repository(db: AsyncSession, repository: Repository, repo_root: Path) -> None:
    """Embeds and stores every not-yet-indexed file belonging to `repository`."""
    result = await db.execute(
        select(RepositoryFile).where(
            RepositoryFile.repository_id == repository.id, RepositoryFile.is_indexed.is_(False)
        )
    )
    files = list(result.scalars().all())

    for repository_file in files:
        await index_repository_file(db, repository, repository_file, repo_root)
