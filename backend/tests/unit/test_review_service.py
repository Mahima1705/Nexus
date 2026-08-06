import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ExternalServiceException
from app.models.review_history import ReviewInputType
from app.models.user import User
from app.services import llm_service, review_service
from tests.conftest import FakeLLMProvider

pytestmark = pytest.mark.asyncio


async def _make_user(db_session: AsyncSession) -> User:
    user = User(email="reviewer@nexus.ai", hashed_password="x")
    db_session.add(user)
    await db_session.flush()
    return user


async def test_review_code_persists_normalized_result(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    canned = (
        '{"bugs": [{"description": "off-by-one", "line": 12, "severity": "medium"}], '
        '"security_issues": [], "code_smells": [], "performance_suggestions": [], "best_practices": []}'
    )
    monkeypatch.setattr(llm_service, "get_llm_provider", lambda: FakeLLMProvider(response_text=canned))

    user = await _make_user(db_session)
    review = await review_service.review_code(
        db_session,
        user,
        source_code="def foo(): pass",
        language="python",
        input_type=ReviewInputType.SNIPPET,
        input_reference=None,
    )

    assert review.id is not None
    assert review.review_result["bugs"] == [{"description": "off-by-one", "line": 12, "severity": "medium"}]
    assert review.review_result["security_issues"] == []
    assert review.user_id == user.id
    assert review.repository_id is None


async def test_review_code_fills_missing_categories_with_empty_lists(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(llm_service, "get_llm_provider", lambda: FakeLLMProvider(response_text="{}"))

    user = await _make_user(db_session)
    review = await review_service.review_code(
        db_session,
        user,
        source_code="def foo(): pass",
        language="python",
        input_type=ReviewInputType.SNIPPET,
        input_reference=None,
    )

    assert review.review_result == {
        "bugs": [],
        "security_issues": [],
        "code_smells": [],
        "performance_suggestions": [],
        "best_practices": [],
    }


async def test_review_code_ignores_non_list_category_values(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        llm_service, "get_llm_provider", lambda: FakeLLMProvider(response_text='{"bugs": "not a list"}')
    )

    user = await _make_user(db_session)
    review = await review_service.review_code(
        db_session,
        user,
        source_code="def foo(): pass",
        language="python",
        input_type=ReviewInputType.SNIPPET,
        input_reference=None,
    )

    assert review.review_result["bugs"] == []


async def test_review_code_raises_external_service_exception_on_unparseable_response(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(llm_service, "get_llm_provider", lambda: FakeLLMProvider(response_text="not json"))

    user = await _make_user(db_session)
    with pytest.raises(ExternalServiceException):
        await review_service.review_code(
            db_session,
            user,
            source_code="def foo(): pass",
            language="python",
            input_type=ReviewInputType.SNIPPET,
            input_reference=None,
        )
