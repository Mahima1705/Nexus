import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.repository import RepositoryCreateFromGitHub, RepositoryRead
from app.services.repository_service import (
    RepositoryService,
    process_github_repository,
    process_zip_repository,
)

router = APIRouter()


@router.post("/github", response_model=RepositoryRead, status_code=status.HTTP_201_CREATED)
async def create_repository_from_github(
    payload: RepositoryCreateFromGitHub,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RepositoryRead:
    """Registers a GitHub repository and kicks off cloning + file indexing in the background."""
    repository = await RepositoryService(db).create_from_github(current_user, payload)
    background_tasks.add_task(process_github_repository, repository.id)
    return repository


@router.post("/upload", response_model=RepositoryRead, status_code=status.HTTP_201_CREATED)
async def upload_repository_zip(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    description: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RepositoryRead:
    """Uploads a ZIP archive and kicks off extraction + file indexing in the background."""
    repository, zip_path = await RepositoryService(db).create_from_zip(current_user, file, name, description)
    background_tasks.add_task(process_zip_repository, repository.id, zip_path)
    return repository


@router.get("", response_model=list[RepositoryRead])
async def list_repositories(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[RepositoryRead]:
    return await RepositoryService(db).list_for_user(current_user)


@router.get("/{repository_id}", response_model=RepositoryRead)
async def get_repository(
    repository_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RepositoryRead:
    return await RepositoryService(db).get_owned(current_user, repository_id)


@router.delete("/{repository_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repository(
    repository_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await RepositoryService(db).delete(current_user, repository_id)
