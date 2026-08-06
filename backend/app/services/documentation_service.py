"""Documentation Generator: README, Project Overview, Folder Structure, API
Summary, Installation Guide, Environment Variables, or Full documentation.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.prompts.chat_prompts import build_context_prompt, build_repository_prompt
from app.ai.prompts.docs_prompts import DOCUMENTATION_SYSTEM_PROMPT, build_documentation_user_prompt
from app.core.exceptions import BadRequestException
from app.models.documentation_history import DocumentationHistory, DocumentationType
from app.models.repository import Repository, RepositoryStatus
from app.models.repository_file import RepositoryFile
from app.models.user import User
from app.services import llm_service, retriever_service

# Retrieval query per doc type — steers the RAG search toward content that's
# actually useful for that section rather than a generic repository-name query.
_QUERY_BY_DOC_TYPE: dict[DocumentationType, str] = {
    DocumentationType.README: "project overview main features entry point",
    DocumentationType.PROJECT_OVERVIEW: "project architecture main modules",
    DocumentationType.API_SUMMARY: "API routes endpoints controllers",
    DocumentationType.INSTALLATION_GUIDE: "dependencies package manager setup configuration",
    DocumentationType.ENV_VARIABLES: "environment variables configuration settings .env",
    DocumentationType.FULL: "project overview architecture API routes installation environment variables",
}


async def _folder_structure_text(db: AsyncSession, repository_id: uuid.UUID) -> str:
    result = await db.execute(
        select(RepositoryFile.file_path)
        .where(RepositoryFile.repository_id == repository_id)
        .order_by(RepositoryFile.file_path)
    )
    paths = [path for (path,) in result.all()]
    return "\n".join(paths) if paths else "(no files indexed)"


async def _repository_languages(db: AsyncSession, repository_id: uuid.UUID) -> list[str]:
    result = await db.execute(
        select(RepositoryFile.language)
        .where(RepositoryFile.repository_id == repository_id, RepositoryFile.language.is_not(None))
        .distinct()
    )
    return [language for (language,) in result.all()]


async def generate_documentation(
    db: AsyncSession, user: User, repository: Repository, doc_type: DocumentationType
) -> DocumentationHistory:
    if doc_type == DocumentationType.FOLDER_STRUCTURE:
        # Deterministic from our own file records — no LLM call, no hallucination risk.
        content = "```\n" + await _folder_structure_text(db, repository.id) + "\n```"
    else:
        if repository.status != RepositoryStatus.READY:
            raise BadRequestException(f"Repository is not ready yet (status: {repository.status.value}).")

        languages = await _repository_languages(db, repository.id)
        repository_prompt = build_repository_prompt(repository.name, repository.total_files, languages)

        query = _QUERY_BY_DOC_TYPE.get(doc_type, repository.name)
        chunks = await retriever_service.retrieve_relevant_chunks(
            repository.qdrant_collection_name, query, top_k=12
        )
        context_prompt = build_context_prompt(chunks)

        messages = [
            {"role": "system", "content": DOCUMENTATION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": build_documentation_user_prompt(doc_type.value, repository_prompt, context_prompt),
            },
        ]

        provider = llm_service.get_llm_provider()
        content = await provider.complete(messages)

    documentation = DocumentationHistory(
        repository_id=repository.id, user_id=user.id, doc_type=doc_type, content=content
    )
    db.add(documentation)
    await db.commit()
    await db.refresh(documentation)
    return documentation
