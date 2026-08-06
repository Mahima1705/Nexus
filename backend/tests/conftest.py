"""Shared pytest fixtures."""
from typing import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.ai.embeddings.base import EmbeddingProvider
from app.ai.providers.base import LLMProvider
from app.db.base import Base


class FakeEmbeddingProvider(EmbeddingProvider):
    """Deterministic, offline stand-in for a real embedding provider.

    Never hit a real (paid, rate-limited) embedding API from the automated test
    suite — this returns a fixed-size vector derived from each text's length so
    tests can still assert on shape/ordering without any network dependency.
    """

    def __init__(self, dimensions: int = 8) -> None:
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text) % 10) / 10.0] * self._dimensions for text in texts]


class FakeLLMProvider(LLMProvider):
    """Deterministic, offline stand-in for a real LLM provider.

    Never hit a real (paid) chat-completion API from the automated test suite.
    Returns "{}" for JSON-mode requests (every service's result-normalizer treats
    missing keys as empty/default, so this exercises the full pipeline without
    needing a canned response per test) or a fixed override when constructed with one.
    """

    def __init__(self, response_text: str | None = None) -> None:
        self._response_text = response_text

    async def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: str = "text",
    ) -> str:
        if self._response_text is not None:
            return self._response_text
        if response_format == "json":
            return "{}"
        last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        return f"Fake answer based on: {last_user[:80]}"

    async def stream(self, messages: list[dict[str, str]], temperature: float | None = None, max_tokens: int | None = None):
        text = await self.complete(messages, temperature, max_tokens)
        for word in text.split():
            yield word + " "


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """A fresh in-memory SQLite database, schema created, torn down after the test.

    Used for fast unit tests of models/services. Integration tests that need
    real Postgres-specific behavior belong in tests/integration and should
    target settings.DATABASE_URL instead.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def client(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[TestClient]:
    """A TestClient wired to an isolated in-memory SQLite DB via dependency override.

    StaticPool keeps a single shared connection alive for the whole test so every
    request (each of which opens its own AsyncSession) sees the same in-memory data
    instead of a fresh empty database per connection.
    """
    from app.api.deps import get_db
    from app.main import app
    from app.middleware.rate_limit import limiter

    # The rate limiter's in-memory storage is a process-wide singleton, so quota
    # consumed by an earlier test would otherwise leak into this one and cause
    # spurious 429s unrelated to what this test is actually checking.
    limiter.reset()

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    # FastAPI's dependency_overrides only reach endpoint dependencies. Background
    # tasks (repository clone/extract/index) sit outside the DI system and open
    # their own session via `AsyncSessionLocal` imported directly into
    # repository_service — patch that name so they hit the same test DB instead
    # of the real (and here, unavailable) Postgres instance.
    import app.services.embedding_service as embedding_service_module
    import app.services.llm_service as llm_service_module
    import app.services.repository_service as repository_service_module
    import app.services.retriever_service as retriever_service_module

    monkeypatch.setattr(repository_service_module, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(embedding_service_module, "get_embedding_provider", lambda: FakeEmbeddingProvider())
    monkeypatch.setattr(llm_service_module, "get_llm_provider", lambda: FakeLLMProvider())

    # retriever_service bare-imports its own copy of get_embedding_provider, separate
    # from embedding_service's — both need patching independently. search() defaults
    # to returning no chunks, which is correct here since the Qdrant upsert itself is
    # also stubbed below (no test repository ever has real vectors stored); endpoint
    # tests that need non-empty retrieval results override this themselves.
    monkeypatch.setattr(retriever_service_module, "get_embedding_provider", lambda: FakeEmbeddingProvider())

    async def _empty_search(collection_name: str, query_vector: list[float], top_k: int = 8, score_threshold=None):
        return []

    monkeypatch.setattr(retriever_service_module, "search", _empty_search)

    # Likewise, never depend on a real Qdrant instance being reachable for the fast
    # unit-test suite — real Qdrant behavior (collection create/upsert/search) is
    # covered separately by tests/integration/test_qdrant_live.py, which skips
    # itself when Qdrant isn't running instead of silently no-op'ing.
    async def _noop_ensure_collection(collection_name: str, vector_size: int) -> None:
        return None

    async def _noop_upsert_chunks(collection_name: str, points: list) -> None:
        return None

    monkeypatch.setattr(embedding_service_module, "ensure_collection", _noop_ensure_collection)
    monkeypatch.setattr(embedding_service_module, "upsert_chunks", _noop_upsert_chunks)

    async def _noop_delete_collection(collection_name: str) -> None:
        return None

    monkeypatch.setattr(repository_service_module, "delete_collection", _noop_delete_collection)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    await engine.dispose()
