"""Targets the failure/edge-case branches of repository_service.py that the
happy-path endpoint tests (test_repositories.py) never exercise: upload size
limits, oversized repositories, and the background pipeline's exception handling.
"""
import io
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.exceptions import BadRequestException
from app.db.base import Base
from app.models.repository import Repository, RepositorySourceType, RepositoryStatus
from app.models.user import User
from app.services import repository_service
from app.services.repository_service import (
    RepositoryService,
    _index_repository_files,
    process_github_repository,
    process_zip_repository,
)

pytestmark = pytest.mark.asyncio


async def _make_user_and_repository(
    db_session: AsyncSession, source_type: RepositorySourceType = RepositorySourceType.ZIP
) -> tuple[User, Repository]:
    user = User(email="repoowner@nexus.ai", hashed_password="x")
    db_session.add(user)
    await db_session.flush()

    repository = Repository(
        owner_id=user.id,
        name="demo",
        source_type=source_type,
        source_url="https://github.com/octocat/Hello-World" if source_type == RepositorySourceType.GITHUB else None,
        status=RepositoryStatus.PENDING,
        qdrant_collection_name="nexus_repo_service_test",
    )
    db_session.add(repository)
    await db_session.commit()
    await db_session.refresh(repository)
    return user, repository


@pytest_asyncio.fixture
async def static_pool_session_factory(monkeypatch: pytest.MonkeyPatch):
    """Background tasks open their own session via AsyncSessionLocal; StaticPool
    keeps everything on one shared in-memory connection so a session opened here
    (to seed data) and a session opened later (by the background task) see the
    same data.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(repository_service, "AsyncSessionLocal", session_factory)

    yield session_factory

    await engine.dispose()


class _FakeUploadFile:
    """Minimal UploadFile-like double that yields more bytes than a tiny size limit."""

    def __init__(self, total_bytes: int) -> None:
        self.filename = "big-repo.zip"
        self._remaining = total_bytes

    async def read(self, size: int) -> bytes:
        if self._remaining <= 0:
            return b""
        chunk_size = min(size, self._remaining)
        self._remaining -= chunk_size
        return b"x" * chunk_size


async def test_create_from_zip_rejects_upload_exceeding_size_limit(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 1)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))

    user = User(email="uploader2@nexus.ai", hashed_password="x")
    db_session.add(user)
    await db_session.flush()

    oversized_upload = _FakeUploadFile(total_bytes=2 * 1024 * 1024)  # 2MB > 1MB limit

    with pytest.raises(BadRequestException):
        await RepositoryService(db_session).create_from_zip(user, oversized_upload, name=None, description=None)

    result = await db_session.execute(select(Repository).where(Repository.owner_id == user.id))
    repository = result.scalar_one()
    assert repository.status == RepositoryStatus.FAILED
    assert "exceeds" in repository.status_message

    # The partially-written zip must not be left behind on disk.
    assert list(tmp_path.glob("*.zip")) == []


async def test_index_repository_files_rejects_oversized_repository(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(settings, "MAX_REPO_SIZE_MB", 0)

    _user, repository = await _make_user_and_repository(db_session)
    (tmp_path / "main.py").write_text("print('hello')\n")

    with pytest.raises(BadRequestException):
        await _index_repository_files(db_session, repository, tmp_path)


async def test_process_github_repository_marks_failed_when_clone_raises(
    static_pool_session_factory, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(settings, "REPOS_DIR", str(tmp_path))

    async with static_pool_session_factory() as seed_session:
        _user, repository = await _make_user_and_repository(seed_session, RepositorySourceType.GITHUB)
        repository_id = repository.id

    monkeypatch.setattr(
        repository_service, "clone_repository", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("clone failed"))
    )

    await process_github_repository(repository_id)

    async with static_pool_session_factory() as check_session:
        refreshed = await check_session.get(Repository, repository_id)
        assert refreshed.status == RepositoryStatus.FAILED
        assert "clone failed" in refreshed.status_message
    assert not (tmp_path / str(repository_id)).exists()


async def test_process_github_repository_noop_when_repository_missing(
    static_pool_session_factory,
) -> None:
    import uuid

    # Must not raise even though no such repository exists (e.g. deleted mid-clone).
    await process_github_repository(uuid.uuid4())


async def test_process_zip_repository_marks_failed_when_extraction_raises(
    static_pool_session_factory, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(settings, "REPOS_DIR", str(tmp_path))

    async with static_pool_session_factory() as seed_session:
        _user, repository = await _make_user_and_repository(seed_session, RepositorySourceType.ZIP)
        repository_id = repository.id

    zip_path = tmp_path / f"{repository_id}.zip"
    zip_path.write_bytes(b"not a real zip")

    monkeypatch.setattr(
        repository_service,
        "extract_zip_safely",
        lambda *a, **k: (_ for _ in ()).throw(BadRequestException("corrupt archive")),
    )

    await process_zip_repository(repository_id, zip_path)

    async with static_pool_session_factory() as check_session:
        refreshed = await check_session.get(Repository, repository_id)
        assert refreshed.status == RepositoryStatus.FAILED
        assert "corrupt archive" in refreshed.status_message
    assert not zip_path.exists()  # cleaned up even on failure (finally block)


async def test_delete_removes_local_files_and_qdrant_collection(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repos_dir = tmp_path / "repos"
    uploads_dir = tmp_path / "uploads"
    repos_dir.mkdir()
    uploads_dir.mkdir()
    monkeypatch.setattr(settings, "REPOS_DIR", str(repos_dir))
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(uploads_dir))

    user, repository = await _make_user_and_repository(db_session)

    (repos_dir / str(repository.id)).mkdir()
    (repos_dir / str(repository.id) / "main.py").write_text("print(1)")
    (uploads_dir / f"{repository.id}.zip").write_bytes(b"zip bytes")

    fake_delete_collection = AsyncMock()
    monkeypatch.setattr(repository_service, "delete_collection", fake_delete_collection)

    await RepositoryService(db_session).delete(user, repository.id)

    assert not (repos_dir / str(repository.id)).exists()
    assert not (uploads_dir / f"{repository.id}.zip").exists()
    fake_delete_collection.assert_awaited_once_with(repository.qdrant_collection_name)

    result = await db_session.get(Repository, repository.id)
    assert result is None
