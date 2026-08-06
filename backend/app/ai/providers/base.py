"""Provider-agnostic chat-completion interface. Every LLM backend implements this."""
from abc import ABC, abstractmethod
from typing import AsyncIterator, Literal


class LLMProvider(ABC):
    @abstractmethod
    async def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: Literal["text", "json"] = "text",
    ) -> str:
        """Returns the full completion text for an OpenAI-style message list
        (roles: system/user/assistant)."""

    @abstractmethod
    def stream(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Yields incremental text chunks as they're generated."""
