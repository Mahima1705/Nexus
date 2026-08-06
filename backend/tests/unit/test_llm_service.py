import pytest

from app.ai.providers.claude_provider import ClaudeLLMProvider
from app.ai.providers.openai_provider import OpenAILLMProvider
from app.core.config import settings
from app.core.exceptions import BadRequestException
from app.services import llm_service


def test_get_llm_provider_returns_openai_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "LLM_PROVIDER", "openai")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")  # SDK requires a key at construction time
    llm_service.get_llm_provider.cache_clear()

    provider = llm_service.get_llm_provider()

    assert isinstance(provider, OpenAILLMProvider)
    llm_service.get_llm_provider.cache_clear()


def test_get_llm_provider_returns_claude_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "LLM_PROVIDER", "claude")
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "test-key")
    llm_service.get_llm_provider.cache_clear()

    provider = llm_service.get_llm_provider()

    assert isinstance(provider, ClaudeLLMProvider)
    llm_service.get_llm_provider.cache_clear()


def test_get_llm_provider_rejects_unsupported_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "LLM_PROVIDER", "not-a-real-provider")
    llm_service.get_llm_provider.cache_clear()

    with pytest.raises(BadRequestException):
        llm_service.get_llm_provider()

    llm_service.get_llm_provider.cache_clear()
