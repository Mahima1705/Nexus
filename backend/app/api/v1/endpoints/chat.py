import json
import uuid

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.chat import ChatSessionCreate, ChatSessionRead, MessageCreate, MessageRead
from app.services import chat_service
from app.services.repository_service import RepositoryService

router = APIRouter()


@router.post(
    "/repositories/{repository_id}/sessions",
    response_model=ChatSessionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_chat_session(
    repository_id: uuid.UUID,
    payload: ChatSessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatSessionRead:
    repository = await RepositoryService(db).get_owned(current_user, repository_id)
    return await chat_service.create_session(db, repository, current_user, payload.title)


@router.get("/repositories/{repository_id}/sessions", response_model=list[ChatSessionRead])
async def list_chat_sessions(
    repository_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ChatSessionRead]:
    repository = await RepositoryService(db).get_owned(current_user, repository_id)
    return await chat_service.list_sessions_for_repository(db, repository, current_user)


@router.get("/sessions/{session_id}/messages", response_model=list[MessageRead])
async def list_messages(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MessageRead]:
    session = await chat_service.get_owned_session(db, current_user, session_id)
    return await chat_service.list_messages(db, session.id)


@router.post("/sessions/{session_id}/messages", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
async def ask_question(
    session_id: uuid.UUID,
    payload: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageRead:
    session = await chat_service.get_owned_session(db, current_user, session_id)
    repository = await RepositoryService(db).get_owned(current_user, session.repository_id)
    return await chat_service.ask(db, repository, session, payload.content)


@router.post("/sessions/{session_id}/messages/stream")
async def ask_question_stream(
    session_id: uuid.UUID,
    payload: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Server-Sent Events stream of the assistant's answer as it's generated.

    Each event is a JSON object on its own `data: ` line:
        {"type": "chunk", "content": "..."}   -- one per token/delta
        {"type": "done", "message": {...}}    -- the final persisted Message
        {"type": "error", "message": "..."}   -- terminal
    """
    session = await chat_service.get_owned_session(db, current_user, session_id)
    repository = await RepositoryService(db).get_owned(current_user, session.repository_id)

    async def event_stream():
        async for event in chat_service.ask_stream(db, repository, session, payload.content):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
