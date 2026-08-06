"""Live end-to-end retrieval test: real Qdrant, a deterministic fixed-vector fake
embedding provider standing in for OpenAI/BGE (which would need a real API key /
model weights). Proves retriever_service actually talks to Qdrant correctly, not
just that its mocked unit tests pass.
"""
import socket
from urllib.parse import urlparse

import pytest

from app.ai.embeddings.base import EmbeddingProvider
from app.ai.vector_store.qdrant_client import delete_collection, ensure_collection, upsert_chunks
from app.core.config import settings
from app.services import retriever_service


def _qdrant_available() -> bool:
    parsed = urlparse(settings.QDRANT_URL)
    try:
        socket.create_connection((parsed.hostname, parsed.port), timeout=2).close()
        return True
    except OSError:
        return False


pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(not _qdrant_available(), reason="Qdrant is not reachable")]

_TEST_COLLECTION = "nexus_repo_retrieval_test"


class _FixedVectorProvider(EmbeddingProvider):
    def __init__(self, vector_by_text: dict[str, list[float]], default: list[float]) -> None:
        self._vector_by_text = vector_by_text
        self._default = default

    @property
    def dimensions(self) -> int:
        return len(self._default)

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._vector_by_text.get(text, self._default) for text in texts]


@pytest.fixture(autouse=True)
async def _clean_collection():
    await delete_collection(_TEST_COLLECTION)
    yield
    await delete_collection(_TEST_COLLECTION)


async def test_retrieve_relevant_chunks_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    await ensure_collection(_TEST_COLLECTION, vector_size=4)
    await upsert_chunks(
        _TEST_COLLECTION,
        [
            (
                "11111111-1111-1111-1111-111111111111",
                [1.0, 0.0, 0.0, 0.0],
                {
                    "file_path": "auth.py",
                    "language": "python",
                    "content": "def login(): ...",
                    "start_line": 1,
                    "end_line": 3,
                    "chunk_index": 0,
                },
            ),
            (
                "22222222-2222-2222-2222-222222222222",
                [0.0, 1.0, 0.0, 0.0],
                {
                    "file_path": "payments.py",
                    "language": "python",
                    "content": "def charge(): ...",
                    "start_line": 1,
                    "end_line": 3,
                    "chunk_index": 0,
                },
            ),
        ],
    )

    query = "how does login work?"
    provider = _FixedVectorProvider({query: [1.0, 0.0, 0.0, 0.0]}, default=[0.0, 0.0, 0.0, 1.0])
    monkeypatch.setattr(retriever_service, "get_embedding_provider", lambda: provider)

    results = await retriever_service.retrieve_relevant_chunks(_TEST_COLLECTION, query, top_k=1)

    assert len(results) == 1
    assert results[0].file_path == "auth.py"
    assert results[0].content == "def login(): ..."
    assert results[0].score > 0.9
