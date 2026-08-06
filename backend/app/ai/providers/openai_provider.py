"""OpenAI chat-completion provider (the default), built on LangChain's ChatOpenAI —
see app.services.llm_service for how the active provider is selected."""
from typing import AsyncIterator, Literal

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

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


def _to_langchain_messages(messages: list[dict[str, str]]) -> list[BaseMessage]:
    return [_ROLE_TO_MESSAGE_CLASS.get(m["role"], HumanMessage)(content=m["content"]) for m in messages]


class OpenAILLMProvider(LLMProvider):
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self._model = model or settings.OPENAI_CHAT_MODEL
        self._api_key = api_key or settings.OPENAI_API_KEY

    def _build_chat_model(
        self,
        temperature: float | None,
        max_tokens: int | None,
        response_format: Literal["text", "json"],
    ) -> ChatOpenAI:
        model_kwargs: dict = {}
        if response_format == "json":
            model_kwargs["response_format"] = {"type": "json_object"}
        return ChatOpenAI(
            api_key=self._api_key,
            model=self._model,
            temperature=temperature if temperature is not None else settings.LLM_TEMPERATURE,
            max_tokens=max_tokens or settings.LLM_MAX_TOKENS,
            model_kwargs=model_kwargs,
        )

    async def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: Literal["text", "json"] = "text",
    ) -> str:
        try:
            chat_model = self._build_chat_model(temperature, max_tokens, response_format)
            response = await chat_model.ainvoke(_to_langchain_messages(messages))
        except Exception as exc:
            logger.warning("OpenAI chat completion failed: %s", exc)
            raise ExternalServiceException(f"OpenAI chat completion failed: {exc}") from exc

        return response.content or ""

    async def stream(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        try:
            chat_model = self._build_chat_model(temperature, max_tokens, "text")
            async for chunk in chat_model.astream(_to_langchain_messages(messages)):
                if chunk.content:
                    yield chunk.content
        except Exception as exc:
            logger.warning("OpenAI chat stream failed: %s", exc)
            raise ExternalServiceException(f"OpenAI chat stream failed: {exc}") from exc
