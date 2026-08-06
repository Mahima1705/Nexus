from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.errors import ErrorAnalysisRequest, ErrorAnalysisResponse
from app.services import error_analysis_service
from app.services.repository_service import RepositoryService

router = APIRouter()


@router.post("/analyze", response_model=ErrorAnalysisResponse)
async def analyze_error(
    payload: ErrorAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ErrorAnalysisResponse:
    repository = None
    if payload.repository_id is not None:
        repository = await RepositoryService(db).get_owned(current_user, payload.repository_id)

    result = await error_analysis_service.analyze_error(payload.error_text, repository)
    return ErrorAnalysisResponse(**result)
