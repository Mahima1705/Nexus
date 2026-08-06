"""Provider-agnostic embedding interface. Every embedding backend implements this."""
from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    @property
    @abstractmethod
    def dimensions(self) -> int:
        """The length of vectors this provider produces — must match the Qdrant
        collection's configured vector size."""

    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embeds a batch of texts, returning one vector per input in the same order."""

    async def embed_query(self, text: str) -> list[float]:
        """Convenience wrapper for embedding a single query string."""
        vectors = await self.embed_texts([text])
        return vectors[0]
