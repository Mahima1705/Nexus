"""OpenAI embeddings provider (the default), built on LangChain's OpenAIEmbeddings —
see app.services.embedding_service for how the active provider is selected.

Batching and retry are delegated to OpenAIEmbeddings' own `chunk_size`/`max_retries`
rather than hand-rolled here.
"""
from langchain_openai import OpenAIEmbeddings

from app.ai.embeddings.base import EmbeddingProvider
from app.core.config import settings
from app.core.exceptions import ExternalServiceException
from app.core.logging import get_logger

logger = get_logger(__name__)

_DIMENSIONS_BY_MODEL = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self._model = model or settings.OPENAI_EMBEDDING_MODEL
        self._api_key = api_key or settings.OPENAI_API_KEY
        self._client: OpenAIEmbeddings | None = None  # lazy: seam for tests, avoids eager client construction

    def _get_client(self) -> OpenAIEmbeddings:
        if self._client is None:
            self._client = OpenAIEmbeddings(
                api_key=self._api_key,
                model=self._model,
                chunk_size=96,
                max_retries=3,
            )
        return self._client

    @property
    def dimensions(self) -> int:
        return _DIMENSIONS_BY_MODEL.get(self._model, settings.VECTOR_SIZE)

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            return await self._get_client().aembed_documents(texts)
        except Exception as exc:
            logger.warning("OpenAI embedding request failed: %s", exc)
            raise ExternalServiceException(f"OpenAI embedding request failed: {exc}") from exc
