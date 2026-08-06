"""Live test against a real Qdrant instance (e.g. `docker run -p 6333:6333 qdrant/qdrant`).

Skipped automatically when Qdrant isn't reachable. Everything else in the suite
runs fully offline — this is the deliberate exception, alongside the live GitHub
clone test, because "does the real Qdrant wire protocol actually accept our
collection config and point IDs" can't be verified against a mock.
"""
import socket
from urllib.parse import urlparse

import pytest

from app.ai.vector_store.qdrant_client import (
    delete_collection,
    ensure_collection,
    get_qdrant_client,
    search,
    upsert_chunks,
)
from app.core.config import settings


def _qdrant_available() -> bool:
    parsed = urlparse(settings.QDRANT_URL)
    try:
        socket.create_connection((parsed.hostname, parsed.port), timeout=2).close()
        return True
    except OSError:
        return False


pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(not _qdrant_available(), reason="Qdrant is not reachable")]

_TEST_COLLECTION = "nexus_repo_integration_test"


@pytest.fixture(autouse=True)
async def _clean_collection():
    await delete_collection(_TEST_COLLECTION)
    yield
    await delete_collection(_TEST_COLLECTION)


async def test_ensure_collection_is_idempotent() -> None:
    await ensure_collection(_TEST_COLLECTION, vector_size=8)
    await ensure_collection(_TEST_COLLECTION, vector_size=8)  # second call must not raise

    client = get_qdrant_client()
    assert await client.collection_exists(_TEST_COLLECTION)


async def test_upsert_and_search_round_trip() -> None:
    await ensure_collection(_TEST_COLLECTION, vector_size=8)

    await upsert_chunks(
        _TEST_COLLECTION,
        [
            ("11111111-1111-1111-1111-111111111111", [1.0] * 8, {"file_path": "a.py", "content": "def a(): pass"}),
            ("22222222-2222-2222-2222-222222222222", [0.0] * 8, {"file_path": "b.py", "content": "def b(): pass"}),
        ],
    )

    results = await search(_TEST_COLLECTION, query_vector=[1.0] * 8, top_k=1)

    assert len(results) == 1
    assert results[0].payload["file_path"] == "a.py"
    assert str(results[0].id) == "11111111-1111-1111-1111-111111111111"


async def test_delete_collection_removes_it() -> None:
    await ensure_collection(_TEST_COLLECTION, vector_size=8)
    client = get_qdrant_client()
    assert await client.collection_exists(_TEST_COLLECTION)

    await delete_collection(_TEST_COLLECTION)

    assert not await client.collection_exists(_TEST_COLLECTION)
