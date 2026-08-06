"""Repository, context, and user prompt templates for the codebase chat feature."""
from app.services.retriever_service import RetrievedChunk


def build_repository_prompt(repository_name: str, total_files: int, languages: list[str]) -> str:
    lang_summary = ", ".join(languages) if languages else "unknown"
    return (
        f"Repository: {repository_name}\n"
        f"Indexed files: {total_files}\n"
        f"Primary languages: {lang_summary}"
    )


def build_context_prompt(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "No relevant repository context was found for this query."

    blocks = []
    for i, chunk in enumerate(chunks, start=1):
        location = (
            f"{chunk.file_path}:{chunk.start_line}-{chunk.end_line}"
            if chunk.start_line is not None
            else chunk.file_path
        )
        lang_tag = chunk.language or ""
        blocks.append(
            f"[Source {i}: {location}] (relevance: {chunk.score:.2f})\n```{lang_tag}\n{chunk.content}\n```"
        )
    return "\n\n".join(blocks)


def build_user_prompt(question: str, context_prompt: str) -> str:
    return (
        f"Repository context:\n{context_prompt}\n\n"
        f"Question: {question}\n\n"
        "Answer using only the repository context above. Cite sources as described in your instructions."
    )
