import pytest

from app.core.exceptions import BadRequestException, ExternalServiceException
from app.models.repository import Repository, RepositorySourceType, RepositoryStatus
from app.services import llm_service, retriever_service, search_service
from tests.conftest import FakeEmbeddingProvider, FakeLLMProvider

pytestmark = pytest.mark.asyncio


def _make_repository(status: RepositoryStatus = RepositoryStatus.READY) -> Repository:
    return Repository(
        owner_id="00000000-0000-0000-0000-000000000000",
        name="demo",
        source_type=RepositorySourceType.ZIP,
        status=status,
        qdrant_collection_name="nexus_repo_search_test",
        total_files=3,
    )


async def test_search_raises_if_repository_not_ready() -> None:
    repository = _make_repository(status=RepositoryStatus.INDEXING)

    with pytest.raises(BadRequestException):
        await search_service.search(repository, "where is login handled?")


async def test_search_returns_normalized_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(retriever_service, "get_embedding_provider", lambda: FakeEmbeddingProvider())

    async def _empty_search(*args, **kwargs):
        return []

    monkeypatch.setattr(retriever_service, "search", _empty_search)

    canned = (
        '{"relevant_files": [{"file_path": "auth.py", "reason": "handles login"}], '
        '"explanation": "Login is handled here.", "reasoning": "Found via login keyword match."}'
    )
    monkeypatch.setattr(llm_service, "get_llm_provider", lambda: FakeLLMProvider(response_text=canned))

    repository = _make_repository()
    result = await search_service.search(repository, "where is login handled?")

    assert result["relevant_files"] == [{"file_path": "auth.py", "reason": "handles login"}]
    assert result["explanation"] == "Login is handled here."
    assert result["reasoning"] == "Found via login keyword match."


async def test_search_normalizes_missing_keys_to_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(retriever_service, "get_embedding_provider", lambda: FakeEmbeddingProvider())

    async def _empty_search(*args, **kwargs):
        return []

    monkeypatch.setattr(retriever_service, "search", _empty_search)
    monkeypatch.setattr(llm_service, "get_llm_provider", lambda: FakeLLMProvider(response_text="{}"))

    repository = _make_repository()
    result = await search_service.search(repository, "where is login handled?")

    assert result == {"relevant_files": [], "explanation": "", "reasoning": ""}


async def test_search_raises_external_service_exception_on_unparseable_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(retriever_service, "get_embedding_provider", lambda: FakeEmbeddingProvider())

    async def _empty_search(*args, **kwargs):
        return []

    monkeypatch.setattr(retriever_service, "search", _empty_search)
    monkeypatch.setattr(llm_service, "get_llm_provider", lambda: FakeLLMProvider(response_text="not json"))

    repository = _make_repository()
    with pytest.raises(ExternalServiceException):
        await search_service.search(repository, "where is login handled?")
