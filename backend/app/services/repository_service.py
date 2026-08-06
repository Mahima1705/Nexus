"""Repository CRUD plus the background clone/extract/index pipeline.

The two `process_*` functions are queued via FastAPI BackgroundTasks and run
*after* the request's own DB session has already been closed, so they open a
fresh AsyncSession of their own via AsyncSessionLocal rather than reusing the
one injected into the endpoint.
"""
import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.vector_store.qdrant_client import delete_collection
from app.core.config import settings
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.repository import Repository, RepositorySourceType, RepositoryStatus
from app.models.repository_file import RepositoryFile
from app.models.user import User
from app.repository_processor.file_filter import detect_language, iter_repository_files
from app.repository_processor.github_cloner import clone_repository
from app.repository_processor.zip_extractor import extract_zip_safely
from app.schemas.repository import RepositoryCreateFromGitHub
from app.services.embedding_service import index_repository
from app.utils.file_utils import compute_sha256, directory_size_bytes
from app.utils.validators import validate_github_url, validate_zip_upload_filename

logger = get_logger(__name__)


class RepositoryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_for_user(self, user: User) -> list[Repository]:
        result = await self.db.execute(
            select(Repository).where(Repository.owner_id == user.id).order_by(Repository.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_owned(self, user: User, repository_id: uuid.UUID) -> Repository:
        result = await self.db.execute(select(Repository).where(Repository.id == repository_id))
        repository = result.scalar_one_or_none()
        if repository is None:
            raise NotFoundException("Repository not found.")
        if repository.owner_id != user.id:
            raise ForbiddenException("You do not have access to this repository.")
        return repository

    async def create_from_github(self, user: User, payload: RepositoryCreateFromGitHub) -> Repository:
        _owner, repo_name = validate_github_url(payload.source_url)

        repository = Repository(
            owner_id=user.id,
            name=payload.name or repo_name,
            description=payload.description,
            source_type=RepositorySourceType.GITHUB,
            source_url=payload.source_url,
            status=RepositoryStatus.PENDING,
            qdrant_collection_name=f"{settings.QDRANT_COLLECTION_PREFIX}{uuid.uuid4().hex}",
        )
        self.db.add(repository)
        await self.db.commit()
        await self.db.refresh(repository)
        return repository

    async def create_from_zip(
        self, user: User, upload: UploadFile, name: str | None, description: str | None
    ) -> tuple[Repository, Path]:
        validate_zip_upload_filename(upload)

        repository = Repository(
            owner_id=user.id,
            name=name or Path(upload.filename or "uploaded-repo").stem,
            description=description,
            source_type=RepositorySourceType.ZIP,
            status=RepositoryStatus.PENDING,
            qdrant_collection_name=f"{settings.QDRANT_COLLECTION_PREFIX}{uuid.uuid4().hex}",
        )
        self.db.add(repository)
        await self.db.commit()
        await self.db.refresh(repository)

        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        zip_path = upload_dir / f"{repository.id}.zip"

        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        written = 0
        try:
            with zip_path.open("wb") as f:
                while chunk := await upload.read(1024 * 1024):
                    written += len(chunk)
                    if written > max_bytes:
                        raise BadRequestException(
                            f"Uploaded file exceeds the {settings.MAX_UPLOAD_SIZE_MB}MB limit."
                        )
                    f.write(chunk)
        except BadRequestException:
            zip_path.unlink(missing_ok=True)
            repository.status = RepositoryStatus.FAILED
            repository.status_message = f"Upload exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit."
            await self.db.commit()
            raise

        return repository, zip_path

    async def delete(self, user: User, repository_id: uuid.UUID) -> None:
        repository = await self.get_owned(user, repository_id)
        shutil.rmtree(Path(settings.REPOS_DIR) / str(repository.id), ignore_errors=True)
        (Path(settings.UPLOAD_DIR) / f"{repository.id}.zip").unlink(missing_ok=True)
        await delete_collection(repository.qdrant_collection_name)
        await self.db.delete(repository)
        await self.db.commit()


async def _index_repository_files(db: AsyncSession, repository: Repository, repo_dir: Path) -> None:
    total_size = directory_size_bytes(repo_dir)
    max_bytes = settings.MAX_REPO_SIZE_MB * 1024 * 1024
    if total_size > max_bytes:
        raise BadRequestException(f"Repository exceeds the {settings.MAX_REPO_SIZE_MB}MB size limit.")

    max_file_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    count = 0
    for absolute_path, relative_path in iter_repository_files(repo_dir):
        size_bytes = absolute_path.stat().st_size
        content_hash = (
            compute_sha256(absolute_path) if size_bytes <= max_file_bytes else "skipped:file-too-large"
        )

        db.add(
            RepositoryFile(
                repository_id=repository.id,
                file_path=str(relative_path).replace("\\", "/"),
                language=detect_language(absolute_path),
                size_bytes=size_bytes,
                content_hash=content_hash,
                is_indexed=False,  # flips to True once chunked + embedded (Milestone 6-8)
            )
        )
        count += 1

    repository.total_files = count
    await db.commit()


async def process_github_repository(repository_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Repository).where(Repository.id == repository_id))
        repository = result.scalar_one_or_none()
        if repository is None:
            return

        repo_dir = Path(settings.REPOS_DIR) / str(repository.id)
        try:
            repository.status = RepositoryStatus.CLONING
            await db.commit()

            repository.default_branch = clone_repository(repository.source_url, repo_dir)
            await db.commit()

            await _index_repository_files(db, repository, repo_dir)

            repository.status = RepositoryStatus.INDEXING
            await db.commit()

            await index_repository(db, repository, repo_dir)

            repository.status = RepositoryStatus.READY
            await db.commit()
            logger.info(
                "Cloned and embedded repository %s (%s files, %s chunks)",
                repository.id,
                repository.total_files,
                repository.total_chunks,
            )
        except Exception as exc:
            logger.exception("Failed to process GitHub repository %s", repository_id)
            repository.status = RepositoryStatus.FAILED
            repository.status_message = str(exc)[:1000]
            await db.commit()
            shutil.rmtree(repo_dir, ignore_errors=True)


async def process_zip_repository(repository_id: uuid.UUID, zip_path: Path) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Repository).where(Repository.id == repository_id))
        repository = result.scalar_one_or_none()
        if repository is None:
            zip_path.unlink(missing_ok=True)
            return

        repo_dir = Path(settings.REPOS_DIR) / str(repository.id)
        try:
            repository.status = RepositoryStatus.EXTRACTING
            await db.commit()

            extract_zip_safely(zip_path, repo_dir)
            await _index_repository_files(db, repository, repo_dir)

            repository.status = RepositoryStatus.INDEXING
            await db.commit()

            await index_repository(db, repository, repo_dir)

            repository.status = RepositoryStatus.READY
            await db.commit()
            logger.info(
                "Extracted and embedded repository %s (%s files, %s chunks)",
                repository.id,
                repository.total_files,
                repository.total_chunks,
            )
        except Exception as exc:
            logger.exception("Failed to process ZIP repository %s", repository_id)
            repository.status = RepositoryStatus.FAILED
            repository.status_message = str(exc)[:1000]
            await db.commit()
            shutil.rmtree(repo_dir, ignore_errors=True)
        finally:
            zip_path.unlink(missing_ok=True)
