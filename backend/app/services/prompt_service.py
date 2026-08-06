"""Composes the system, developer, repository, context, and user prompts into the
final message list handed to an LLM provider (Milestone 10).

Each prompt type from the spec maps to a distinct, independently-testable piece:
    System Prompt      -> app.ai.prompts.system_prompts.SYSTEM_PROMPT
    Developer Prompt    -> app.ai.prompts.system_prompts.DEVELOPER_PROMPT
    Repository Prompt   -> app.ai.prompts.chat_prompts.build_repository_prompt
    Context Prompt       -> app.ai.prompts.chat_prompts.build_context_prompt
    User Prompt          -> app.ai.prompts.chat_prompts.build_user_prompt
This module is where they're assembled together.
"""
from app.ai.prompts.chat_prompts import build_context_prompt, build_repository_prompt, build_user_prompt
from app.ai.prompts.system_prompts import DEVELOPER_PROMPT, SYSTEM_PROMPT
from app.services.retriever_service import RetrievedChunk


def build_chat_messages(
    question: str,
    chunks: list[RetrievedChunk],
    repository_name: str,
    total_files: int,
    languages: list[str],
    conversation_history: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    """Returns an OpenAI/Claude-compatible list of {"role", "content"} messages.

    Order: system (persona + repository grounding) -> developer (formatting rules)
    -> prior conversation turns, if any -> user (question + retrieved context).
    """
    system_content = f"{SYSTEM_PROMPT}\n\n{build_repository_prompt(repository_name, total_files, languages)}"

    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_content},
        {"role": "system", "content": DEVELOPER_PROMPT},
    ]

    if conversation_history:
        messages.extend(conversation_history)

    context_prompt = build_context_prompt(chunks)
    messages.append({"role": "user", "content": build_user_prompt(question, context_prompt)})

    return messages
