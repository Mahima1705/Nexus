import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.search import SearchRequest, SearchResponse
from app.services import search_service
from app.services.repository_service import RepositoryService

router = APIRouter()


@router.post("/repositories/{repository_id}/search", response_model=SearchResponse)
async def smart_code_search(
    repository_id: uuid.UUID,
    payload: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    repository = await RepositoryService(db).get_owned(current_user, repository_id)
    result = await search_service.search(repository, payload.query)
    return SearchResponse(**result)
