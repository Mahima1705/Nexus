from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.models.message import MessageRole
from app.models.repository import Repository, RepositorySourceType, RepositoryStatus
from app.models.user import User
from app.services import chat_service, llm_service, retriever_service
from tests.conftest import FakeEmbeddingProvider, FakeLLMProvider

pytestmark = pytest.mark.asyncio


def _make_scored_point(payload: dict, score: float) -> MagicMock:
    point = MagicMock()
    point.payload = payload
    point.score = score
    return point


async def _make_user_and_repository(db_session: AsyncSession, status: RepositoryStatus = RepositoryStatus.READY) -> tuple[User, Repository]:
    user = User(email="chatter@nexus.ai", hashed_password="x")
    db_session.add(user)
    await db_session.flush()

    repository = Repository(
        owner_id=user.id,
        name="demo",
        source_type=RepositorySourceType.ZIP,
        status=status,
        qdrant_collection_name="nexus_repo_chat_test",
        total_files=5,
    )
    db_session.add(repository)
    await db_session.flush()
    return user, repository


async def test_ask_raises_if_repository_not_ready(db_session: AsyncSession) -> None:
    user, repository = await _make_user_and_repository(db_session, status=RepositoryStatus.INDEXING)
    session = await chat_service.create_session(db_session, repository, user, title=None)

    with pytest.raises(BadRequestException):
        await chat_service.ask(db_session, repository, session, "How does auth work?")


async def test_ask_persists_user_and_assistant_messages(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(retriever_service, "get_embedding_provider", lambda: FakeEmbeddingProvider())
    monkeypatch.setattr(
        retriever_service,
        "search",
        lambda *a, **k: _fake_search_result(),
    )
    monkeypatch.setattr(llm_service, "get_llm_provider", lambda: FakeLLMProvider(response_text="JWT is created in auth.py."))

    user, repository = await _make_user_and_repository(db_session)
    session = await chat_service.create_session(db_session, repository, user, title="Auth question")

    assistant_message = await chat_service.ask(db_session, repository, session, "How does JWT auth work?")

    assert assistant_message.role == MessageRole.ASSISTANT
    assert assistant_message.content == "JWT is created in auth.py."
    assert assistant_message.referenced_files[0]["file_path"] == "auth.py"

    messages = await chat_service.list_messages(db_session, session.id)
    assert [m.role for m in messages] == [MessageRole.USER, MessageRole.ASSISTANT]
    assert messages[0].content == "How does JWT auth work?"


async def _fake_search_result():
    return [
        _make_scored_point(
            {
                "file_path": "auth.py",
                "language": "python",
                "content": "def create_token(): ...",
                "start_line": 1,
                "end_line": 5,
                "chunk_index": 0,
            },
            score=0.9,
        )
    ]


async def test_ask_includes_conversation_history_on_second_question(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(retriever_service, "get_embedding_provider", lambda: FakeEmbeddingProvider())

    async def _empty_search(*args, **kwargs):
        return []

    monkeypatch.setattr(retriever_service, "search", _empty_search)
    monkeypatch.setattr(llm_service, "get_llm_provider", lambda: FakeLLMProvider())

    user, repository = await _make_user_and_repository(db_session)
    session = await chat_service.create_session(db_session, repository, user, title=None)

    await chat_service.ask(db_session, repository, session, "first question")
    await chat_service.ask(db_session, repository, session, "second question")

    messages = await chat_service.list_messages(db_session, session.id)
    assert len(messages) == 4


async def test_get_owned_session_raises_not_found(db_session: AsyncSession) -> None:
    import uuid

    user, _repository = await _make_user_and_repository(db_session)
    with pytest.raises(NotFoundException):
        await chat_service.get_owned_session(db_session, user, uuid.uuid4())


async def test_get_owned_session_raises_forbidden_for_other_users_session(db_session: AsyncSession) -> None:
    owner, repository = await _make_user_and_repository(db_session)
    session = await chat_service.create_session(db_session, repository, owner, title=None)

    other_user = User(email="intruder@nexus.ai", hashed_password="x")
    db_session.add(other_user)
    await db_session.flush()

    with pytest.raises(ForbiddenException):
        await chat_service.get_owned_session(db_session, other_user, session.id)


async def test_ask_stream_yields_chunks_then_done_with_persisted_message(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(retriever_service, "get_embedding_provider", lambda: FakeEmbeddingProvider())

    async def _empty_search(*args, **kwargs):
        return []

    monkeypatch.setattr(retriever_service, "search", _empty_search)
    monkeypatch.setattr(llm_service, "get_llm_provider", lambda: FakeLLMProvider(response_text="Hello world"))

    user, repository = await _make_user_and_repository(db_session)
    session = await chat_service.create_session(db_session, repository, user, title=None)

    events = [event async for event in chat_service.ask_stream(db_session, repository, session, "hi")]

    chunk_events = [e for e in events if e["type"] == "chunk"]
    done_events = [e for e in events if e["type"] == "done"]
    assert len(done_events) == 1
    assert len(chunk_events) > 0
    assert "".join(e["content"] for e in chunk_events).strip() == "Hello world"

    final_message = done_events[0]["message"]
    assert final_message["role"] == "assistant"
    assert final_message["content"].strip() == "Hello world"

    persisted = await chat_service.list_messages(db_session, session.id)
    assert [m.role.value for m in persisted] == ["user", "assistant"]
    assert persisted[0].content == "hi"


async def test_ask_stream_yields_error_event_if_repository_not_ready(db_session: AsyncSession) -> None:
    user, repository = await _make_user_and_repository(db_session, status=RepositoryStatus.INDEXING)
    session = await chat_service.create_session(db_session, repository, user, title=None)

    events = [event async for event in chat_service.ask_stream(db_session, repository, session, "hi")]

    assert len(events) == 1
    assert events[0]["type"] == "error"

    persisted = await chat_service.list_messages(db_session, session.id)
    assert persisted == []


async def test_ask_stream_persists_user_message_even_if_stream_fails(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.core.exceptions import ExternalServiceException

    monkeypatch.setattr(retriever_service, "get_embedding_provider", lambda: FakeEmbeddingProvider())

    async def _empty_search(*args, **kwargs):
        return []

    monkeypatch.setattr(retriever_service, "search", _empty_search)

    class _FailingProvider(FakeLLMProvider):
        async def stream(self, messages, temperature=None, max_tokens=None):
            raise ExternalServiceException("provider unavailable")
            yield  # pragma: no cover - makes this an async generator

    monkeypatch.setattr(llm_service, "get_llm_provider", lambda: _FailingProvider())

    user, repository = await _make_user_and_repository(db_session)
    session = await chat_service.create_session(db_session, repository, user, title=None)

    events = [event async for event in chat_service.ask_stream(db_session, repository, session, "hi")]

    assert events[-1]["type"] == "error"

    persisted = await chat_service.list_messages(db_session, session.id)
    assert len(persisted) == 1
    assert persisted[0].role.value == "user"
