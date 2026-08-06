from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.ai.providers.claude_provider import ClaudeLLMProvider, _to_langchain_messages as claude_to_lc
from app.ai.providers.openai_provider import OpenAILLMProvider, _to_langchain_messages as openai_to_lc
from app.core.exceptions import ExternalServiceException

pytestmark = pytest.mark.asyncio


class _FakeChatModel:
    def __init__(self, response_content: str = "Hello.", stream_chunks: list[str] | None = None, error: Exception | None = None) -> None:
        self._response_content = response_content
        self._stream_chunks = stream_chunks or []
        self._error = error

    async def ainvoke(self, messages):
        if self._error:
            raise self._error
        return AIMessage(content=self._response_content)

    async def astream(self, messages):
        if self._error:
            raise self._error
        for chunk in self._stream_chunks:
            yield AIMessage(content=chunk)


# --- message conversion ---


async def test_openai_to_langchain_messages_maps_roles() -> None:
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]
    converted = openai_to_lc(messages)

    assert isinstance(converted[0], SystemMessage)
    assert isinstance(converted[1], HumanMessage)
    assert isinstance(converted[2], AIMessage)
    assert converted[0].content == "sys"


async def test_claude_to_langchain_messages_appends_json_instruction_as_system() -> None:
    messages = [{"role": "user", "content": "hi"}]
    converted = claude_to_lc(messages, extra_system_suffix="Respond with JSON only.")

    assert isinstance(converted[-1], SystemMessage)
    assert converted[-1].content == "Respond with JSON only."


# --- OpenAI provider ---


async def test_openai_complete_returns_response_content(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OpenAILLMProvider(api_key="test-key")
    monkeypatch.setattr(provider, "_build_chat_model", lambda *a, **k: _FakeChatModel("Hello from the model."))

    result = await provider.complete([{"role": "user", "content": "hi"}])

    assert result == "Hello from the model."


async def test_openai_complete_requests_json_response_format(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OpenAILLMProvider(api_key="test-key")
    captured = {}

    def _build(temperature, max_tokens, response_format):
        captured["response_format"] = response_format
        return _FakeChatModel("{}")

    monkeypatch.setattr(provider, "_build_chat_model", _build)

    await provider.complete([{"role": "user", "content": "hi"}], response_format="json")

    assert captured["response_format"] == "json"


async def test_openai_complete_wraps_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OpenAILLMProvider(api_key="test-key")
    monkeypatch.setattr(provider, "_build_chat_model", lambda *a, **k: _FakeChatModel(error=RuntimeError("boom")))

    with pytest.raises(ExternalServiceException):
        await provider.complete([{"role": "user", "content": "hi"}])


async def test_openai_stream_yields_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OpenAILLMProvider(api_key="test-key")
    monkeypatch.setattr(provider, "_build_chat_model", lambda *a, **k: _FakeChatModel(stream_chunks=["Hel", "lo"]))

    chunks = [chunk async for chunk in provider.stream([{"role": "user", "content": "hi"}])]

    assert chunks == ["Hel", "lo"]


# --- Claude provider ---


async def test_claude_complete_returns_response_content(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = ClaudeLLMProvider(api_key="test-key")
    monkeypatch.setattr(provider, "_build_chat_model", lambda *a, **k: _FakeChatModel("Hello from Claude."))

    result = await provider.complete([{"role": "user", "content": "hi"}])

    assert result == "Hello from Claude."


async def test_claude_complete_wraps_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = ClaudeLLMProvider(api_key="test-key")
    monkeypatch.setattr(provider, "_build_chat_model", lambda *a, **k: _FakeChatModel(error=RuntimeError("boom")))

    with pytest.raises(ExternalServiceException):
        await provider.complete([{"role": "user", "content": "hi"}])


async def test_claude_stream_yields_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = ClaudeLLMProvider(api_key="test-key")
    monkeypatch.setattr(provider, "_build_chat_model", lambda *a, **k: _FakeChatModel(stream_chunks=["Hi", " there"]))

    chunks = [chunk async for chunk in provider.stream([{"role": "user", "content": "hi"}])]

    assert chunks == ["Hi", " there"]
