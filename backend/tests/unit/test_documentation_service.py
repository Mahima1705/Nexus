import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException
from app.models.documentation_history import DocumentationType
from app.models.repository import Repository, RepositorySourceType, RepositoryStatus
from app.models.repository_file import RepositoryFile
from app.models.user import User
from app.services import documentation_service, llm_service, retriever_service
from tests.conftest import FakeEmbeddingProvider, FakeLLMProvider

pytestmark = pytest.mark.asyncio


async def _make_user_and_repository(
    db_session: AsyncSession, status: RepositoryStatus = RepositoryStatus.READY
) -> tuple[User, Repository]:
    user = User(email="docwriter@nexus.ai", hashed_password="x")
    db_session.add(user)
    await db_session.flush()

    repository = Repository(
        owner_id=user.id,
        name="demo",
        source_type=RepositorySourceType.ZIP,
        status=status,
        qdrant_collection_name="nexus_repo_docs_test",
        total_files=2,
    )
    db_session.add(repository)
    await db_session.flush()
    return user, repository


async def test_folder_structure_is_generated_deterministically_without_llm(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _fail_if_called():
        raise AssertionError("LLM should not be called for FOLDER_STRUCTURE")

    monkeypatch.setattr(llm_service, "get_llm_provider", _fail_if_called)

    user, repository = await _make_user_and_repository(db_session, status=RepositoryStatus.INDEXING)
    db_session.add_all(
        [
            RepositoryFile(
                repository_id=repository.id,
                file_path="src/main.py",
                language="python",
                size_bytes=10,
                content_hash="a",
                is_indexed=True,
            ),
            RepositoryFile(
                repository_id=repository.id,
                file_path="README.md",
                language="markdown",
                size_bytes=10,
                content_hash="b",
                is_indexed=True,
            ),
        ]
    )
    await db_session.commit()

    doc = await documentation_service.generate_documentation(
        db_session, user, repository, DocumentationType.FOLDER_STRUCTURE
    )

    assert "README.md" in doc.content
    assert "src/main.py" in doc.content
    assert doc.doc_type == DocumentationType.FOLDER_STRUCTURE


async def test_folder_structure_works_even_if_repository_not_ready(db_session: AsyncSession) -> None:
    user, repository = await _make_user_and_repository(db_session, status=RepositoryStatus.INDEXING)

    doc = await documentation_service.generate_documentation(
        db_session, user, repository, DocumentationType.FOLDER_STRUCTURE
    )

    assert "(no files indexed)" in doc.content


async def test_readme_generation_raises_if_repository_not_ready(db_session: AsyncSession) -> None:
    user, repository = await _make_user_and_repository(db_session, status=RepositoryStatus.INDEXING)

    with pytest.raises(BadRequestException):
        await documentation_service.generate_documentation(db_session, user, repository, DocumentationType.README)


async def test_readme_generation_persists_llm_content(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(retriever_service, "get_embedding_provider", lambda: FakeEmbeddingProvider())

    async def _empty_search(*args, **kwargs):
        return []

    monkeypatch.setattr(retriever_service, "search", _empty_search)
    monkeypatch.setattr(
        llm_service, "get_llm_provider", lambda: FakeLLMProvider(response_text="# demo\n\nA cool project.")
    )

    user, repository = await _make_user_and_repository(db_session, status=RepositoryStatus.READY)

    doc = await documentation_service.generate_documentation(db_session, user, repository, DocumentationType.README)

    assert doc.content == "# demo\n\nA cool project."
    assert doc.doc_type == DocumentationType.README
    assert doc.repository_id == repository.id
    assert doc.user_id == user.id
