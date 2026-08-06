from app.ai.prompts.chat_prompts import build_context_prompt, build_repository_prompt, build_user_prompt
from app.ai.prompts.system_prompts import DEVELOPER_PROMPT, SYSTEM_PROMPT
from app.services.prompt_service import build_chat_messages
from app.services.retriever_service import RetrievedChunk


def _make_chunk(**overrides) -> RetrievedChunk:
    defaults = dict(
        file_path="src/auth/jwt.py",
        language="python",
        content="def create_token(): ...",
        start_line=10,
        end_line=25,
        chunk_index=0,
        score=0.87,
    )
    defaults.update(overrides)
    return RetrievedChunk(**defaults)


def test_system_prompt_instructs_against_hallucination() -> None:
    assert "ONLY using the repository context" in SYSTEM_PROMPT
    assert "don't have enough information" in SYSTEM_PROMPT.lower() or "do not have enough information" in SYSTEM_PROMPT.lower()


def test_developer_prompt_specifies_source_citation_format() -> None:
    assert "Source N" in DEVELOPER_PROMPT


def test_build_repository_prompt_includes_name_files_and_languages() -> None:
    prompt = build_repository_prompt("nexus-demo", 42, ["python", "typescript"])
    assert "nexus-demo" in prompt
    assert "42" in prompt
    assert "python" in prompt
    assert "typescript" in prompt


def test_build_repository_prompt_handles_no_languages() -> None:
    prompt = build_repository_prompt("empty-repo", 0, [])
    assert "unknown" in prompt


def test_build_context_prompt_with_no_chunks_says_so_explicitly() -> None:
    prompt = build_context_prompt([])
    assert "No relevant repository context" in prompt


def test_build_context_prompt_labels_sources_with_file_and_lines() -> None:
    chunks = [_make_chunk(file_path="a.py", start_line=1, end_line=5), _make_chunk(file_path="b.py", start_line=None, end_line=None)]
    prompt = build_context_prompt(chunks)

    assert "[Source 1: a.py:1-5]" in prompt
    assert "[Source 2: b.py]" in prompt
    assert "```python" in prompt


def test_build_user_prompt_includes_question_and_context() -> None:
    prompt = build_user_prompt("How does auth work?", "some context block")
    assert "How does auth work?" in prompt
    assert "some context block" in prompt


def test_build_chat_messages_ordering_and_roles() -> None:
    chunks = [_make_chunk()]
    messages = build_chat_messages(
        question="How does auth work?",
        chunks=chunks,
        repository_name="nexus-demo",
        total_files=10,
        languages=["python"],
    )

    assert [m["role"] for m in messages] == ["system", "system", "user"]
    assert "nexus-demo" in messages[0]["content"]
    assert messages[1]["content"] == DEVELOPER_PROMPT
    assert "How does auth work?" in messages[-1]["content"]
    assert "src/auth/jwt.py" in messages[-1]["content"]


def test_build_chat_messages_includes_conversation_history_between_system_and_user() -> None:
    history = [
        {"role": "user", "content": "earlier question"},
        {"role": "assistant", "content": "earlier answer"},
    ]

    messages = build_chat_messages(
        question="follow-up question",
        chunks=[],
        repository_name="nexus-demo",
        total_files=1,
        languages=["python"],
        conversation_history=history,
    )

    assert [m["role"] for m in messages] == ["system", "system", "user", "assistant", "user"]
    assert messages[2]["content"] == "earlier question"
    assert messages[3]["content"] == "earlier answer"
    assert "follow-up question" in messages[-1]["content"]
