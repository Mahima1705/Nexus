from unittest.mock import AsyncMock

import pytest

from app.ai.vector_store import qdrant_client as qdrant_client_module
from app.ai.vector_store.qdrant_client import (
    delete_collection,
    ensure_collection,
    search,
    upsert_chunks,
)
from app.core.exceptions import ExternalServiceException

pytestmark = pytest.mark.asyncio


class _FakeQdrantClient:
    def __init__(self) -> None:
        self.collection_exists = AsyncMock(return_value=False)
        self.create_collection = AsyncMock()
        self.upsert = AsyncMock()
        self.query_points = AsyncMock()
        self.delete_collection = AsyncMock()


@pytest.fixture
def fake_client(monkeypatch: pytest.MonkeyPatch) -> _FakeQdrantClient:
    client = _FakeQdrantClient()
    monkeypatch.setattr(qdrant_client_module, "get_qdrant_client", lambda: client)
    return client


async def test_ensure_collection_creates_when_missing(fake_client: _FakeQdrantClient) -> None:
    fake_client.collection_exists.return_value = False

    await ensure_collection("nexus_repo_x", vector_size=1536)

    fake_client.create_collection.assert_awaited_once()


async def test_ensure_collection_skips_creation_when_already_exists(fake_client: _FakeQdrantClient) -> None:
    fake_client.collection_exists.return_value = True

    await ensure_collection("nexus_repo_x", vector_size=1536)

    fake_client.create_collection.assert_not_awaited()


async def test_ensure_collection_wraps_errors(fake_client: _FakeQdrantClient) -> None:
    fake_client.collection_exists.side_effect = RuntimeError("connection refused")

    with pytest.raises(ExternalServiceException):
        await ensure_collection("nexus_repo_x", vector_size=1536)


async def test_upsert_chunks_skips_empty_list(fake_client: _FakeQdrantClient) -> None:
    await upsert_chunks("nexus_repo_x", [])
    fake_client.upsert.assert_not_awaited()


async def test_upsert_chunks_wraps_errors(fake_client: _FakeQdrantClient) -> None:
    fake_client.upsert.side_effect = RuntimeError("boom")

    with pytest.raises(ExternalServiceException):
        await upsert_chunks("nexus_repo_x", [("id-1", [0.1], {"file_path": "a.py"})])


async def test_search_wraps_errors(fake_client: _FakeQdrantClient) -> None:
    fake_client.query_points.side_effect = RuntimeError("boom")

    with pytest.raises(ExternalServiceException):
        await search("nexus_repo_x", query_vector=[0.1])


async def test_delete_collection_swallows_errors_instead_of_raising(fake_client: _FakeQdrantClient) -> None:
    fake_client.collection_exists.return_value = True
    fake_client.delete_collection.side_effect = RuntimeError("boom")

    await delete_collection("nexus_repo_x")  # must not raise


async def test_delete_collection_noop_when_collection_missing(fake_client: _FakeQdrantClient) -> None:
    fake_client.collection_exists.return_value = False

    await delete_collection("nexus_repo_x")

    fake_client.delete_collection.assert_not_awaited()
