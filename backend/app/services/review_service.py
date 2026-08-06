"""AI Code Reviewer: analyzes a pasted snippet or uploaded file for bugs, security
issues, code smells, performance problems, and best-practice violations.

Standalone — no repository context/RAG involved, matching the spec's feature
description (review operates on the code the caller provides directly).
"""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.prompts.review_prompts import REVIEW_SYSTEM_PROMPT, build_review_user_prompt
from app.core.exceptions import ExternalServiceException
from app.models.review_history import ReviewHistory, ReviewInputType
from app.models.user import User
from app.services import llm_service
from app.utils.json_utils import extract_json

_REQUIRED_LIST_KEYS = ("bugs", "security_issues", "code_smells", "performance_suggestions", "best_practices")


def _normalize_review_result(raw: dict) -> dict:
    return {key: raw.get(key, []) if isinstance(raw.get(key), list) else [] for key in _REQUIRED_LIST_KEYS}


async def review_code(
    db: AsyncSession,
    user: User,
    source_code: str,
    language: str | None,
    input_type: ReviewInputType,
    input_reference: str | None,
    repository_id: uuid.UUID | None = None,
) -> ReviewHistory:
    messages = [
        {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
        {"role": "user", "content": build_review_user_prompt(source_code, language, input_reference)},
    ]

    provider = llm_service.get_llm_provider()
    raw_response = await provider.complete(messages, response_format="json")

    try:
        parsed = extract_json(raw_response)
    except ValueError as exc:
        raise ExternalServiceException(f"Failed to parse code review response: {exc}") from exc

    review = ReviewHistory(
        repository_id=repository_id,
        user_id=user.id,
        input_type=input_type,
        input_reference=input_reference,
        source_code=source_code,
        language=language,
        review_result=_normalize_review_result(parsed),
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return review
