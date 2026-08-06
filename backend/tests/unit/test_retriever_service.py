from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services import retriever_service
from tests.conftest import FakeEmbeddingProvider

pytestmark = pytest.mark.asyncio


def _make_scored_point(payload: dict, score: float) -> MagicMock:
    point = MagicMock()
    point.payload = payload
    point.score = score
    return point


async def test_retrieve_relevant_chunks_returns_empty_for_blank_query() -> None:
    assert await retriever_service.retrieve_relevant_chunks("nexus_repo_x", "") == []
    assert await retriever_service.retrieve_relevant_chunks("nexus_repo_x", "   ") == []


async def test_retrieve_relevant_chunks_maps_payload_correctly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(retriever_service, "get_embedding_provider", lambda: FakeEmbeddingProvider())

    fake_search = AsyncMock(
        return_value=[
            _make_scored_point(
                {
                    "file_path": "src/auth/jwt.py",
                    "language": "python",
                    "content": "def create_token(): ...",
                    "start_line": 10,
                    "end_line": 25,
                    "chunk_index": 1,
                },
                score=0.92,
            )
        ]
    )
    monkeypatch.setattr(retriever_service, "search", fake_search)

    results = await retriever_service.retrieve_relevant_chunks("nexus_repo_x", "how does auth work?")

    assert len(results) == 1
    chunk = results[0]
    assert chunk.file_path == "src/auth/jwt.py"
    assert chunk.language == "python"
    assert chunk.content == "def create_token(): ..."
    assert chunk.start_line == 10
    assert chunk.end_line == 25
    assert chunk.chunk_index == 1
    assert chunk.score == 0.92


async def test_retrieve_relevant_chunks_passes_top_k_and_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(retriever_service, "get_embedding_provider", lambda: FakeEmbeddingProvider())
    fake_search = AsyncMock(return_value=[])
    monkeypatch.setattr(retriever_service, "search", fake_search)

    await retriever_service.retrieve_relevant_chunks("nexus_repo_x", "query", top_k=3, score_threshold=0.5)

    fake_search.assert_awaited_once()
    _args, kwargs = fake_search.call_args
    assert kwargs["top_k"] == 3
    assert kwargs["score_threshold"] == 0.5


async def test_retrieve_relevant_chunks_uses_configured_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(retriever_service, "get_embedding_provider", lambda: FakeEmbeddingProvider())
    fake_search = AsyncMock(return_value=[])
    monkeypatch.setattr(retriever_service, "search", fake_search)

    await retriever_service.retrieve_relevant_chunks("nexus_repo_x", "query")

    _args, kwargs = fake_search.call_args
    assert kwargs["top_k"] == settings.RETRIEVAL_TOP_K
    assert kwargs["score_threshold"] == settings.RETRIEVAL_SCORE_THRESHOLD


async def test_retrieve_relevant_chunks_skips_points_with_no_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(retriever_service, "get_embedding_provider", lambda: FakeEmbeddingProvider())
    empty_payload_point = MagicMock(payload=None, score=0.1)
    fake_search = AsyncMock(return_value=[empty_payload_point])
    monkeypatch.setattr(retriever_service, "search", fake_search)

    results = await retriever_service.retrieve_relevant_chunks("nexus_repo_x", "query")

    assert results == []
