from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.exceptions import BadRequestException
from app.models.review_history import ReviewInputType
from app.models.user import User
from app.schemas.review import ReviewHistoryRead, ReviewSnippetRequest
from app.services import review_service

router = APIRouter()

_MAX_REVIEW_FILE_SIZE_BYTES = 200 * 1024  # code files don't need more than this


@router.post("/snippet", response_model=ReviewHistoryRead, status_code=status.HTTP_201_CREATED)
async def review_snippet(
    payload: ReviewSnippetRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReviewHistoryRead:
    """Review a pasted code snippet."""
    return await review_service.review_code(
        db,
        current_user,
        source_code=payload.source_code,
        language=payload.language,
        input_type=ReviewInputType.SNIPPET,
        input_reference=payload.filename,
    )


@router.post("/file", response_model=ReviewHistoryRead, status_code=status.HTTP_201_CREATED)
async def review_file(
    file: UploadFile = File(...),
    language: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReviewHistoryRead:
    """Review an uploaded source file."""
    content = await file.read(_MAX_REVIEW_FILE_SIZE_BYTES + 1)
    if len(content) > _MAX_REVIEW_FILE_SIZE_BYTES:
        raise BadRequestException(f"File exceeds the {_MAX_REVIEW_FILE_SIZE_BYTES // 1024}KB review size limit.")

    try:
        source_code = content.decode("utf-8")
    except UnicodeDecodeError:
        source_code = content.decode("latin-1", errors="replace")

    return await review_service.review_code(
        db,
        current_user,
        source_code=source_code,
        language=language,
        input_type=ReviewInputType.FILE,
        input_reference=file.filename,
    )
