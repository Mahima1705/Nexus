"""Smart Code Search: given a natural-language description of where something
lives (or should be added), returns the most relevant files with an explanation.

Ephemeral — there's no search_history table (matching the spec's DB design), so
nothing here is persisted.
"""
from app.ai.prompts.chat_prompts import build_context_prompt, build_repository_prompt
from app.ai.prompts.system_prompts import SEARCH_SYSTEM_PROMPT
from app.core.exceptions import BadRequestException, ExternalServiceException
from app.models.repository import Repository, RepositoryStatus
from app.services import llm_service, retriever_service
from app.utils.json_utils import extract_json

_REQUIRED_KEYS = ("relevant_files", "explanation", "reasoning")


def _normalize_result(raw: dict) -> dict:
    relevant_files = raw.get("relevant_files")
    return {
        "relevant_files": relevant_files if isinstance(relevant_files, list) else [],
        "explanation": raw.get("explanation") if isinstance(raw.get("explanation"), str) else "",
        "reasoning": raw.get("reasoning") if isinstance(raw.get("reasoning"), str) else "",
    }


async def search(repository: Repository, query: str) -> dict:
    if repository.status != RepositoryStatus.READY:
        raise BadRequestException(f"Repository is not ready yet (status: {repository.status.value}).")

    chunks = await retriever_service.retrieve_relevant_chunks(repository.qdrant_collection_name, query)
    context_prompt = build_context_prompt(chunks)
    repository_prompt = build_repository_prompt(repository.name, repository.total_files, [])

    messages = [
        {"role": "system", "content": SEARCH_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"{repository_prompt}\n\nRepository context:\n{context_prompt}\n\nQuestion: {query}",
        },
    ]

    provider = llm_service.get_llm_provider()
    raw_response = await provider.complete(messages, response_format="json")

    try:
        parsed = extract_json(raw_response)
    except ValueError as exc:
        raise ExternalServiceException(f"Failed to parse search response: {exc}") from exc

    return _normalize_result(parsed)
