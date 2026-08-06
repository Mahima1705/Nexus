from unittest.mock import MagicMock

import pytest

from app.core.exceptions import ExternalServiceException
from app.models.repository import Repository, RepositorySourceType, RepositoryStatus
from app.services import error_analysis_service, llm_service, retriever_service
from tests.conftest import FakeEmbeddingProvider, FakeLLMProvider

pytestmark = pytest.mark.asyncio


def _make_repository(status: RepositoryStatus = RepositoryStatus.READY) -> Repository:
    return Repository(
        owner_id="00000000-0000-0000-0000-000000000000",
        name="demo",
        source_type=RepositorySourceType.ZIP,
        status=status,
        qdrant_collection_name="nexus_repo_error_test",
        total_files=3,
    )


async def test_analyze_error_without_repository_context(monkeypatch: pytest.MonkeyPatch) -> None:
    canned = (
        '{"explanation": "Null pointer.", "likely_cause": "Uninitialized variable.", '
        '"relevant_files": [], "debugging_suggestions": ["add a null check"], "possible_fixes": ["initialize x"]}'
    )
    monkeypatch.setattr(llm_service, "get_llm_provider", lambda: FakeLLMProvider(response_text=canned))

    result = await error_analysis_service.analyze_error("NullPointerException at line 10", repository=None)

    assert result["explanation"] == "Null pointer."
    assert result["likely_cause"] == "Uninitialized variable."
    assert result["relevant_files"] == []
    assert result["debugging_suggestions"] == ["add a null check"]
    assert result["possible_fixes"] == ["initialize x"]


async def test_analyze_error_skips_retrieval_when_repository_not_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    search_called = False

    async def _tracked_search(*args, **kwargs):
        nonlocal search_called
        search_called = True
        return []

    monkeypatch.setattr(retriever_service, "get_embedding_provider", lambda: FakeEmbeddingProvider())
    monkeypatch.setattr(retriever_service, "search", _tracked_search)
    monkeypatch.setattr(llm_service, "get_llm_provider", lambda: FakeLLMProvider(response_text="{}"))

    repository = _make_repository(status=RepositoryStatus.INDEXING)
    await error_analysis_service.analyze_error("some error", repository=repository)

    assert search_called is False


async def test_analyze_error_uses_repository_context_when_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    point = MagicMock()
    point.payload = {
        "file_path": "handlers.py",
        "language": "python",
        "content": "def handler(): raise ValueError()",
        "start_line": 1,
        "end_line": 2,
        "chunk_index": 0,
    }
    point.score = 0.8

    monkeypatch.setattr(retriever_service, "get_embedding_provider", lambda: FakeEmbeddingProvider())

    async def _fake_search(*args, **kwargs):
        return [point]

    monkeypatch.setattr(retriever_service, "search", _fake_search)

    captured_messages = {}

    class _CapturingProvider(FakeLLMProvider):
        async def complete(self, messages, temperature=None, max_tokens=None, response_format="text"):
            captured_messages["messages"] = messages
            return "{}"

    monkeypatch.setattr(llm_service, "get_llm_provider", lambda: _CapturingProvider())

    repository = _make_repository(status=RepositoryStatus.READY)
    await error_analysis_service.analyze_error("ValueError raised", repository=repository)

    user_message = captured_messages["messages"][-1]["content"]
    assert "handlers.py" in user_message
    assert "def handler(): raise ValueError()" in user_message


async def test_analyze_error_continues_when_retrieval_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(retriever_service, "get_embedding_provider", lambda: FakeEmbeddingProvider())

    async def _failing_search(*args, **kwargs):
        raise ExternalServiceException("Qdrant unreachable")

    monkeypatch.setattr(retriever_service, "search", _failing_search)
    monkeypatch.setattr(llm_service, "get_llm_provider", lambda: FakeLLMProvider(response_text="{}"))

    repository = _make_repository(status=RepositoryStatus.READY)
    result = await error_analysis_service.analyze_error("some error", repository=repository)

    assert result["relevant_files"] == []


async def test_analyze_error_raises_external_service_exception_on_unparseable_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(llm_service, "get_llm_provider", lambda: FakeLLMProvider(response_text="not json"))

    with pytest.raises(ExternalServiceException):
        await error_analysis_service.analyze_error("some error", repository=None)
