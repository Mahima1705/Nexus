"""AI Codebase Chat: ties retrieval, prompt building, and the LLM together, and
persists the conversation as ChatSession/Message rows.
"""
import uuid
from typing import Any, AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, ExternalServiceException, ForbiddenException, NotFoundException
from app.core.logging import get_logger
from app.models.chat_session import ChatSession
from app.models.message import Message, MessageRole
from app.models.repository import Repository, RepositoryStatus
from app.models.repository_file import RepositoryFile
from app.models.user import User
from app.services import llm_service, retriever_service
from app.services.prompt_service import build_chat_messages
from app.services.retriever_service import RetrievedChunk

_HISTORY_LIMIT = 10
logger = get_logger(__name__)


async def create_session(
    db: AsyncSession, repository: Repository, user: User, title: str | None
) -> ChatSession:
    session = ChatSession(repository_id=repository.id, user_id=user.id, title=title)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_owned_session(db: AsyncSession, user: User, session_id: uuid.UUID) -> ChatSession:
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise NotFoundException("Chat session not found.")
    if session.user_id != user.id:
        raise ForbiddenException("You do not have access to this chat session.")
    return session


async def list_sessions_for_repository(
    db: AsyncSession, repository: Repository, user: User
) -> list[ChatSession]:
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.repository_id == repository.id, ChatSession.user_id == user.id)
        .order_by(ChatSession.created_at.desc())
    )
    return list(result.scalars().all())


async def list_messages(db: AsyncSession, session_id: uuid.UUID) -> list[Message]:
    result = await db.execute(
        select(Message).where(Message.session_id == session_id).order_by(Message.created_at)
    )
    return list(result.scalars().all())


async def _get_conversation_history(db: AsyncSession, session_id: uuid.UUID) -> list[dict[str, str]]:
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(_HISTORY_LIMIT)
    )
    recent = list(reversed(result.scalars().all()))
    return [{"role": m.role.value, "content": m.content} for m in recent]


async def _repository_languages(db: AsyncSession, repository_id: uuid.UUID) -> list[str]:
    result = await db.execute(
        select(RepositoryFile.language)
        .where(RepositoryFile.repository_id == repository_id, RepositoryFile.language.is_not(None))
        .distinct()
    )
    return [language for (language,) in result.all()]


def _build_referenced_files(chunks: list[RetrievedChunk]) -> list[dict] | None:
    referenced_files = [
        {
            "file_path": chunk.file_path,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
            "score": chunk.score,
        }
        for chunk in chunks
    ]
    return referenced_files or None


def _serialize_message(message: Message) -> dict[str, Any]:
    return {
        "id": str(message.id),
        "session_id": str(message.session_id),
        "role": message.role.value,
        "content": message.content,
        "referenced_files": message.referenced_files,
        "created_at": message.created_at.isoformat(),
    }


async def _prepare_chat_messages(
    db: AsyncSession, repository: Repository, session: ChatSession, question: str
) -> tuple[list[dict[str, str]], list[RetrievedChunk]]:
    history = await _get_conversation_history(db, session.id)
    chunks = await retriever_service.retrieve_relevant_chunks(repository.qdrant_collection_name, question)
    languages = await _repository_languages(db, repository.id)

    messages = build_chat_messages(
        question=question,
        chunks=chunks,
        repository_name=repository.name,
        total_files=repository.total_files,
        languages=languages,
        conversation_history=history,
    )
    return messages, chunks


async def ask(db: AsyncSession, repository: Repository, session: ChatSession, question: str) -> Message:
    """Answers `question` grounded in `repository`'s indexed content, persisting both
    the user's question and the assistant's answer as Messages in `session`.
    """
    if repository.status != RepositoryStatus.READY:
        raise BadRequestException(f"Repository is not ready yet (status: {repository.status.value}).")

    messages, chunks = await _prepare_chat_messages(db, repository, session, question)

    provider = llm_service.get_llm_provider()
    answer = await provider.complete(messages)

    user_message = Message(session_id=session.id, role=MessageRole.USER, content=question)
    assistant_message = Message(
        session_id=session.id,
        role=MessageRole.ASSISTANT,
        content=answer,
        referenced_files=_build_referenced_files(chunks),
    )
    db.add_all([user_message, assistant_message])
    await db.commit()
    await db.refresh(assistant_message)
    return assistant_message


async def ask_stream(
    db: AsyncSession, repository: Repository, session: ChatSession, question: str
) -> AsyncIterator[dict[str, Any]]:
    """Same as `ask`, but yields incremental SSE-shaped events as the answer streams in:
        {"type": "chunk", "content": str}   -- one per token/delta
        {"type": "done", "message": {...}}  -- the final persisted assistant Message
        {"type": "error", "message": str}   -- terminal; nothing further follows

    The user's question is persisted immediately (before streaming starts) so it
    survives even if the client disconnects mid-stream. The assistant's answer is
    only persisted once the full response has been generated.
    """
    if repository.status != RepositoryStatus.READY:
        yield {"type": "error", "message": f"Repository is not ready yet (status: {repository.status.value})."}
        return

    messages, chunks = await _prepare_chat_messages(db, repository, session, question)

    user_message = Message(session_id=session.id, role=MessageRole.USER, content=question)
    db.add(user_message)
    await db.commit()

    provider = llm_service.get_llm_provider()
    accumulated = ""
    try:
        async for delta in provider.stream(messages):
            accumulated += delta
            yield {"type": "chunk", "content": delta}
    except ExternalServiceException as exc:
        logger.warning("Chat stream failed for session %s: %s", session.id, exc)
        yield {"type": "error", "message": str(exc)}
        return

    assistant_message = Message(
        session_id=session.id,
        role=MessageRole.ASSISTANT,
        content=accumulated,
        referenced_files=_build_referenced_files(chunks),
    )
    db.add(assistant_message)
    await db.commit()
    await db.refresh(assistant_message)

    yield {"type": "done", "message": _serialize_message(assistant_message)}
