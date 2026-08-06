import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.docs import DocumentationGenerateRequest, DocumentationHistoryRead
from app.services import documentation_service
from app.services.repository_service import RepositoryService

router = APIRouter()


@router.post(
    "/repositories/{repository_id}/generate",
    response_model=DocumentationHistoryRead,
    status_code=status.HTTP_201_CREATED,
)
async def generate_documentation(
    repository_id: uuid.UUID,
    payload: DocumentationGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentationHistoryRead:
    repository = await RepositoryService(db).get_owned(current_user, repository_id)
    return await documentation_service.generate_documentation(db, current_user, repository, payload.doc_type)
