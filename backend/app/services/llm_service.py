"""Selects the configured LLM provider (OpenAI or Claude).

Every caller (chat, search, review, error-analysis, documentation services)
imports this module and calls `llm_service.get_llm_provider()` — never the bare
function name — so tests can swap the provider with a single monkeypatch here
rather than patching five separate call sites.
"""
from functools import lru_cache

from app.ai.providers.base import LLMProvider
from app.core.config import settings
from app.core.exceptions import BadRequestException


@lru_cache
def get_llm_provider() -> LLMProvider:
    if settings.LLM_PROVIDER == "openai":
        from app.ai.providers.openai_provider import OpenAILLMProvider

        return OpenAILLMProvider()
    if settings.LLM_PROVIDER == "claude":
        from app.ai.providers.claude_provider import ClaudeLLMProvider

        return ClaudeLLMProvider()
    raise BadRequestException(f"Unsupported LLM provider: {settings.LLM_PROVIDER}")
