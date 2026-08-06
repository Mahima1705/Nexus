from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat_session import ChatSession
from app.models.documentation_history import DocumentationHistory, DocumentationType
from app.models.embedding_metadata import EmbeddingMetadata
from app.models.message import Message, MessageRole
from app.models.refresh_token import RefreshToken
from app.models.repository import Repository, RepositorySourceType, RepositoryStatus
from app.models.repository_file import RepositoryFile
from app.models.review_history import ReviewHistory, ReviewInputType
from app.models.user import User

pytestmark = pytest.mark.asyncio


async def _create_user_with_repo(session: AsyncSession) -> tuple[User, Repository]:
    user = User(email="dev@nexus.ai", hashed_password="hashed", full_name="Dev User")
    session.add(user)
    await session.flush()

    repo = Repository(
        owner_id=user.id,
        name="example-repo",
        source_type=RepositorySourceType.GITHUB,
        source_url="https://github.com/example/example-repo",
        status=RepositoryStatus.READY,
        qdrant_collection_name="nexus_repo_example",
    )
    session.add(repo)
    await session.flush()
    return user, repo


async def test_user_repository_cascade_delete(db_session: AsyncSession) -> None:
    user, repo = await _create_user_with_repo(db_session)
    await db_session.commit()

    await db_session.delete(user)
    await db_session.commit()

    result = await db_session.execute(select(Repository).where(Repository.id == repo.id))
    assert result.scalar_one_or_none() is None


async def test_repository_file_and_embedding_metadata_link(db_session: AsyncSession) -> None:
    _, repo = await _create_user_with_repo(db_session)

    repo_file = RepositoryFile(
        repository_id=repo.id,
        file_path="src/auth/jwt.py",
        language="python",
        size_bytes=1024,
        content_hash="abc123",
        is_indexed=True,
    )
    db_session.add(repo_file)
    await db_session.flush()

    chunk = EmbeddingMetadata(
        repository_id=repo.id,
        file_id=repo_file.id,
        qdrant_point_id="point-1",
        chunk_index=0,
        file_path="src/auth/jwt.py",
        language="python",
        start_line=1,
        end_line=40,
        token_count=350,
    )
    db_session.add(chunk)
    await db_session.commit()

    result = await db_session.execute(
        select(RepositoryFile)
        .where(RepositoryFile.id == repo_file.id)
        .options(selectinload(RepositoryFile.embedding_metadata))
    )
    fetched = result.scalar_one()
    assert len(fetched.embedding_metadata) == 1
    assert fetched.embedding_metadata[0].qdrant_point_id == "point-1"


async def test_chat_session_message_ordering(db_session: AsyncSession) -> None:
    user, repo = await _create_user_with_repo(db_session)

    chat_session = ChatSession(repository_id=repo.id, user_id=user.id, title="How does auth work?")
    db_session.add(chat_session)
    await db_session.flush()

    db_session.add_all(
        [
            Message(session_id=chat_session.id, role=MessageRole.USER, content="How does JWT auth work?"),
            Message(
                session_id=chat_session.id,
                role=MessageRole.ASSISTANT,
                content="JWT is generated in src/auth/jwt.py ...",
                referenced_files=[{"file_path": "src/auth/jwt.py", "snippet": "def create_token(...)", "score": 0.91}],
            ),
        ]
    )
    await db_session.commit()

    result = await db_session.execute(
        select(ChatSession).where(ChatSession.id == chat_session.id).options(selectinload(ChatSession.messages))
    )
    fetched = result.scalar_one()
    assert [m.role for m in fetched.messages] == [MessageRole.USER, MessageRole.ASSISTANT]
    assert fetched.messages[1].referenced_files[0]["file_path"] == "src/auth/jwt.py"


async def test_review_history_allows_null_repository(db_session: AsyncSession) -> None:
    user = User(email="reviewer@nexus.ai", hashed_password="hashed")
    db_session.add(user)
    await db_session.flush()

    review = ReviewHistory(
        repository_id=None,
        user_id=user.id,
        input_type=ReviewInputType.SNIPPET,
        source_code="def foo(): pass",
        language="python",
        review_result={"bugs": [], "security_issues": [], "code_smells": [], "performance_suggestions": [], "best_practices": []},
    )
    db_session.add(review)
    await db_session.commit()

    result = await db_session.execute(select(ReviewHistory).where(ReviewHistory.id == review.id))
    fetched = result.scalar_one()
    assert fetched.repository_id is None


async def test_documentation_history_records_doc_type(db_session: AsyncSession) -> None:
    user, repo = await _create_user_with_repo(db_session)

    doc = DocumentationHistory(
        repository_id=repo.id, user_id=user.id, doc_type=DocumentationType.README, content="# example-repo"
    )
    db_session.add(doc)
    await db_session.commit()

    result = await db_session.execute(select(DocumentationHistory).where(DocumentationHistory.id == doc.id))
    fetched = result.scalar_one()
    assert fetched.doc_type == DocumentationType.README


async def test_refresh_token_defaults_to_not_revoked(db_session: AsyncSession) -> None:
    user = User(email="token@nexus.ai", hashed_password="hashed")
    db_session.add(user)
    await db_session.flush()

    token = RefreshToken(
        user_id=user.id,
        token_hash="hash123",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db_session.add(token)
    await db_session.commit()

    result = await db_session.execute(select(RefreshToken).where(RefreshToken.id == token.id))
    fetched = result.scalar_one()
    assert fetched.revoked is False
