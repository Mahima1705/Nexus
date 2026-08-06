"""Local BGE embeddings via LangChain's HuggingFaceEmbeddings (sentence-transformers
under the hood) — the no-API-key alternative to OpenAI. Trades a network call + API
cost for a one-time local model download and on-box CPU/GPU inference.
"""
import asyncio

from langchain_huggingface import HuggingFaceEmbeddings

from app.ai.embeddings.base import EmbeddingProvider
from app.core.config import settings

_DIMENSIONS_BY_MODEL = {
    "BAAI/bge-small-en-v1.5": 384,
    "BAAI/bge-base-en-v1.5": 768,
    "BAAI/bge-large-en-v1.5": 1024,
}


class BGEEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model_name: str | None = None) -> None:
        self._model_name = model_name or settings.BGE_MODEL_NAME
        self._client: HuggingFaceEmbeddings | None = None  # lazy: avoid loading the model just to construct this

    def _get_client(self) -> HuggingFaceEmbeddings:
        if self._client is None:
            self._client = HuggingFaceEmbeddings(model_name=self._model_name)
        return self._client

    @property
    def dimensions(self) -> int:
        return _DIMENSIONS_BY_MODEL.get(self._model_name, settings.VECTOR_SIZE)

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        client = self._get_client()
        # HuggingFaceEmbeddings is synchronous/CPU-bound; offload to a worker thread
        # so it doesn't block the event loop that's serving other requests.
        return await asyncio.to_thread(client.embed_documents, texts)
