from unittest.mock import AsyncMock

import pytest

from app.ai.embeddings.bge_embeddings import BGEEmbeddingProvider
from app.ai.embeddings.openai_embeddings import OpenAIEmbeddingProvider
from app.core.exceptions import ExternalServiceException

pytestmark = pytest.mark.asyncio


# --- OpenAI embeddings (LangChain OpenAIEmbeddings under the hood) ---


class _FakeOpenAIEmbeddingsClient:
    def __init__(self, vectors=None, error: Exception | None = None) -> None:
        self._vectors = vectors
        self._error = error
        self.aembed_documents = AsyncMock(side_effect=self._call)

    async def _call(self, texts: list[str]):
        if self._error:
            raise self._error
        return self._vectors


async def test_openai_provider_delegates_to_langchain_client(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OpenAIEmbeddingProvider(api_key="test-key", model="text-embedding-3-small")
    fake_client = _FakeOpenAIEmbeddingsClient(vectors=[[0.1, 0.2], [0.3, 0.4]])
    monkeypatch.setattr(provider, "_get_client", lambda: fake_client)

    vectors = await provider.embed_texts(["a", "b"])

    assert vectors == [[0.1, 0.2], [0.3, 0.4]]
    fake_client.aembed_documents.assert_awaited_once_with(["a", "b"])


async def test_openai_provider_empty_input_returns_empty_list() -> None:
    provider = OpenAIEmbeddingProvider(api_key="test-key")
    assert await provider.embed_texts([]) == []


async def test_openai_provider_wraps_unexpected_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OpenAIEmbeddingProvider(api_key="test-key")
    fake_client = _FakeOpenAIEmbeddingsClient(error=ValueError("boom"))
    monkeypatch.setattr(provider, "_get_client", lambda: fake_client)

    with pytest.raises(ExternalServiceException):
        await provider.embed_texts(["hello"])


async def test_openai_provider_dimensions_known_and_fallback() -> None:
    known = OpenAIEmbeddingProvider(api_key="k", model="text-embedding-3-small")
    assert known.dimensions == 1536

    unknown = OpenAIEmbeddingProvider(api_key="k", model="some-future-model")
    from app.core.config import settings

    assert unknown.dimensions == settings.VECTOR_SIZE


# --- BGE embeddings (LangChain HuggingFaceEmbeddings under the hood) ---


class _FakeHuggingFaceClient:
    def __init__(self, vectors: list[list[float]]) -> None:
        self._vectors = vectors

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._vectors


async def test_bge_provider_embeds_via_local_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mocks the local client so this test doesn't require downloading real BGE
    model weights — exercises our wrapper's async/threading and dimension logic.
    """
    provider = BGEEmbeddingProvider(model_name="BAAI/bge-small-en-v1.5")
    fake_client = _FakeHuggingFaceClient([[0.1, 0.2, 0.3], [0.1, 0.2, 0.3]])
    monkeypatch.setattr(provider, "_get_client", lambda: fake_client)

    vectors = await provider.embed_texts(["hello", "world"])

    assert vectors == [[0.1, 0.2, 0.3], [0.1, 0.2, 0.3]]
    assert provider.dimensions == 384


async def test_bge_provider_empty_input_returns_empty_list() -> None:
    provider = BGEEmbeddingProvider()
    assert await provider.embed_texts([]) == []
