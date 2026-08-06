"""Anthropic Claude chat-completion provider, built on LangChain's ChatAnthropic —
the swappable alternative to OpenAI, selected the same way (app.services.llm_service).

Unlike a hand-rolled Anthropic adapter, ChatAnthropic extracts SystemMessages into
Anthropic's separate `system` parameter and handles the API's turn-alternation
requirements internally, so this module only has to build the message list.
"""
from typing import AsyncIterator, Literal

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.ai.providers.base import LLMProvider
from app.core.config import settings
from app.core.exceptions import ExternalServiceException
from app.core.logging import get_logger

logger = get_logger(__name__)

_ROLE_TO_MESSAGE_CLASS: dict[str, type[BaseMessage]] = {
    "system": SystemMessage,
    "user": HumanMessage,
    "assistant": AIMessage,
}


def _to_langchain_messages(messages: list[dict[str, str]], extra_system_suffix: str = "") -> list[BaseMessage]:
    converted = [_ROLE_TO_MESSAGE_CLASS.get(m["role"], HumanMessage)(content=m["content"]) for m in messages]
    if extra_system_suffix:
        converted.append(SystemMessage(content=extra_system_suffix))
    return converted


class ClaudeLLMProvider(LLMProvider):
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self._model = model or settings.CLAUDE_CHAT_MODEL
        self._api_key = api_key or settings.ANTHROPIC_API_KEY

    def _build_chat_model(self, temperature: float | None, max_tokens: int | None) -> ChatAnthropic:
        return ChatAnthropic(
            api_key=self._api_key,
            model=self._model,
            temperature=temperature if temperature is not None else settings.LLM_TEMPERATURE,
            max_tokens=max_tokens or settings.LLM_MAX_TOKENS,
        )

    async def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: Literal["text", "json"] = "text",
    ) -> str:
        extra_suffix = (
            "Respond with ONLY a valid JSON object. No markdown code fences, no prose outside the JSON."
            if response_format == "json"
            else ""
        )
        try:
            chat_model = self._build_chat_model(temperature, max_tokens)
            response = await chat_model.ainvoke(_to_langchain_messages(messages, extra_suffix))
        except Exception as exc:
            logger.warning("Claude chat completion failed: %s", exc)
            raise ExternalServiceException(f"Claude chat completion failed: {exc}") from exc

        return response.content or ""

    async def stream(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        try:
            chat_model = self._build_chat_model(temperature, max_tokens)
            async for chunk in chat_model.astream(_to_langchain_messages(messages)):
                if chunk.content:
                    yield chunk.content
        except Exception as exc:
            logger.warning("Claude chat stream failed: %s", exc)
            raise ExternalServiceException(f"Claude chat stream failed: {exc}") from exc
