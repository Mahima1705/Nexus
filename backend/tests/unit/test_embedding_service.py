from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.embedding_metadata import EmbeddingMetadata
from app.models.repository import Repository, RepositorySourceType, RepositoryStatus
from app.models.repository_file import RepositoryFile
from app.models.user import User
from app.services import embedding_service
from tests.conftest import FakeEmbeddingProvider

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def stub_qdrant(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Stubs Qdrant calls for every test in this file (never depend on a real
    Qdrant instance for the fast unit suite — see test_qdrant_client.py and
    tests/integration/test_qdrant_live.py for real-Qdrant coverage) while
    recording calls so wiring can still be asserted on.
    """
    calls: dict = {"ensure_collection": [], "upsert_chunks": []}

    async def _ensure_collection(collection_name: str, vector_size: int) -> None:
        calls["ensure_collection"].append((collection_name, vector_size))

    async def _upsert_chunks(collection_name: str, points: list) -> None:
        calls["upsert_chunks"].append((collection_name, points))

    monkeypatch.setattr(embedding_service, "ensure_collection", _ensure_collection)
    monkeypatch.setattr(embedding_service, "upsert_chunks", _upsert_chunks)
    return calls


async def _make_repository(db_session: AsyncSession) -> Repository:
    user = User(email="indexer@nexus.ai", hashed_password="x")
    db_session.add(user)
    await db_session.flush()

    repository = Repository(
        owner_id=user.id,
        name="demo",
        source_type=RepositorySourceType.ZIP,
        status=RepositoryStatus.INDEXING,
        qdrant_collection_name="nexus_repo_test",
    )
    db_session.add(repository)
    await db_session.flush()
    return repository


async def test_index_repository_file_creates_embedding_metadata(
    db_session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(embedding_service, "get_embedding_provider", lambda: FakeEmbeddingProvider())

    repository = await _make_repository(db_session)

    (tmp_path / "main.py").write_text("def foo():\n    return 1\n\n\ndef bar():\n    return 2\n")
    repo_file = RepositoryFile(
        repository_id=repository.id,
        file_path="main.py",
        language="python",
        size_bytes=40,
        content_hash="abc",
        is_indexed=False,
    )
    db_session.add(repo_file)
    await db_session.flush()

    results = await embedding_service.index_repository_file(db_session, repository, repo_file, tmp_path)

    assert len(results) == 2  # two top-level functions -> two chunks
    for _chunk, vector, point_id in results:
        assert len(vector) == 8  # FakeEmbeddingProvider dimensions
        assert point_id

    assert repo_file.is_indexed is True
    assert repository.total_chunks == 2

    stored = await db_session.execute(select(EmbeddingMetadata).where(EmbeddingMetadata.file_id == repo_file.id))
    rows = list(stored.scalars().all())
    assert len(rows) == 2
    assert {row.qdrant_point_id for row in rows} == {point_id for _c, _v, point_id in results}


async def test_index_repository_file_upserts_into_qdrant_with_matching_point_ids(
    db_session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stub_qdrant: dict
) -> None:
    monkeypatch.setattr(embedding_service, "get_embedding_provider", lambda: FakeEmbeddingProvider())

    repository = await _make_repository(db_session)

    (tmp_path / "main.py").write_text("def foo():\n    return 1\n")
    repo_file = RepositoryFile(
        repository_id=repository.id,
        file_path="main.py",
        language="python",
        size_bytes=20,
        content_hash="abc",
        is_indexed=False,
    )
    db_session.add(repo_file)
    await db_session.flush()

    results = await embedding_service.index_repository_file(db_session, repository, repo_file, tmp_path)

    assert stub_qdrant["ensure_collection"] == [(repository.qdrant_collection_name, 8)]
    assert len(stub_qdrant["upsert_chunks"]) == 1

    collection_name, points = stub_qdrant["upsert_chunks"][0]
    assert collection_name == repository.qdrant_collection_name
    assert {point_id for point_id, _vector, _payload in points} == {point_id for _c, _v, point_id in results}

    _point_id, vector, payload = points[0]
    assert vector == results[0][1]
    assert payload["file_path"] == "main.py"
    assert payload["content"] == results[0][0].content
    assert payload["repository_id"] == str(repository.id)


async def test_index_repository_file_skips_binary_files(db_session: AsyncSession, tmp_path: Path) -> None:
    repository = await _make_repository(db_session)

    (tmp_path / "logo.png").write_bytes(b"\x89PNG\r\n")
    repo_file = RepositoryFile(
        repository_id=repository.id,
        file_path="logo.png",
        language=None,
        size_bytes=6,
        content_hash="abc",
        is_indexed=False,
    )
    db_session.add(repo_file)
    await db_session.flush()

    results = await embedding_service.index_repository_file(db_session, repository, repo_file, tmp_path)

    assert results == []
    assert repo_file.is_indexed is False
    assert repository.total_chunks == 0


async def test_index_repository_file_skips_oversized_files(db_session: AsyncSession, tmp_path: Path) -> None:
    repository = await _make_repository(db_session)

    (tmp_path / "huge.py").write_text("x = 1\n")
    repo_file = RepositoryFile(
        repository_id=repository.id,
        file_path="huge.py",
        language="python",
        size_bytes=10_000_000,
        content_hash="skipped:file-too-large",
        is_indexed=False,
    )
    db_session.add(repo_file)
    await db_session.flush()

    results = await embedding_service.index_repository_file(db_session, repository, repo_file, tmp_path)

    assert results == []
    assert repo_file.is_indexed is False


async def test_index_repository_file_with_no_chunks_still_marks_indexed(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    repository = await _make_repository(db_session)

    (tmp_path / "empty.py").write_text("   \n\n")
    repo_file = RepositoryFile(
        repository_id=repository.id,
        file_path="empty.py",
        language="python",
        size_bytes=3,
        content_hash="abc",
        is_indexed=False,
    )
    db_session.add(repo_file)
    await db_session.flush()

    results = await embedding_service.index_repository_file(db_session, repository, repo_file, tmp_path)

    assert results == []
    assert repo_file.is_indexed is True
    assert repository.total_chunks == 0


async def test_index_repository_processes_all_unindexed_files(
    db_session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(embedding_service, "get_embedding_provider", lambda: FakeEmbeddingProvider())

    repository = await _make_repository(db_session)

    (tmp_path / "a.py").write_text("def a():\n    pass\n")
    (tmp_path / "b.py").write_text("def b():\n    pass\n")

    for name in ("a.py", "b.py"):
        db_session.add(
            RepositoryFile(
                repository_id=repository.id,
                file_path=name,
                language="python",
                size_bytes=20,
                content_hash="abc",
                is_indexed=False,
            )
        )
    await db_session.commit()

    await embedding_service.index_repository(db_session, repository, tmp_path)

    result = await db_session.execute(select(RepositoryFile).where(RepositoryFile.repository_id == repository.id))
    files = list(result.scalars().all())
    assert all(f.is_indexed for f in files)
    assert repository.total_chunks == 2
