"""Error & Log Analyzer: explains an exception/stack trace in plain English and
surfaces likely-relevant repository files, if a repository is provided.

Repository context is optional and best-effort — if retrieval fails (e.g. the
repository hasn't finished indexing yet), analysis still proceeds without it
rather than failing the whole request over an enhancement.
"""
from app.ai.prompts.chat_prompts import build_context_prompt
from app.ai.prompts.error_prompts import ERROR_ANALYSIS_SYSTEM_PROMPT, build_error_user_prompt
from app.core.exceptions import ExternalServiceException
from app.core.logging import get_logger
from app.models.repository import Repository, RepositoryStatus
from app.services import llm_service, retriever_service
from app.services.retriever_service import RetrievedChunk
from app.utils.json_utils import extract_json

logger = get_logger(__name__)

_REQUIRED_LIST_KEYS = ("relevant_files", "debugging_suggestions", "possible_fixes")
_REQUIRED_STR_KEYS = ("explanation", "likely_cause")


def _normalize_result(raw: dict) -> dict:
    result: dict = {key: raw.get(key) if isinstance(raw.get(key), str) else "" for key in _REQUIRED_STR_KEYS}
    for key in _REQUIRED_LIST_KEYS:
        value = raw.get(key)
        result[key] = value if isinstance(value, list) else []
    return result


async def _safe_retrieve(repository: Repository, error_text: str) -> list[RetrievedChunk]:
    if repository.status != RepositoryStatus.READY:
        return []
    try:
        return await retriever_service.retrieve_relevant_chunks(repository.qdrant_collection_name, error_text)
    except ExternalServiceException:
        logger.warning("Repository context retrieval failed during error analysis; continuing without it.")
        return []


async def analyze_error(error_text: str, repository: Repository | None) -> dict:
    chunks: list[RetrievedChunk] = []
    if repository is not None:
        chunks = await _safe_retrieve(repository, error_text)

    context_prompt = build_context_prompt(chunks)
    messages = [
        {"role": "system", "content": ERROR_ANALYSIS_SYSTEM_PROMPT},
        {"role": "user", "content": build_error_user_prompt(error_text, context_prompt)},
    ]

    provider = llm_service.get_llm_provider()
    raw_response = await provider.complete(messages, response_format="json")

    try:
        parsed = extract_json(raw_response)
    except ValueError as exc:
        raise ExternalServiceException(f"Failed to parse error analysis response: {exc}") from exc

    return _normalize_result(parsed)
