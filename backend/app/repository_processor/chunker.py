"""Splits file content into semantically-grounded chunks ready for embedding.

Strategy: detect language-appropriate top-level boundaries (function/class
declarations for code, headings for markdown) with lightweight regexes, group
lines between consecutive boundaries into a chunk, then recursively sub-split any
chunk that's still too big with a token-aware sliding window (with overlap so
context isn't lost at the cut). Files in languages with no boundary detector
(json, yaml, plain text, ...) fall straight through to the sliding window.

This is deliberately not a full AST/tree-sitter parser — tree-sitter is called
out as optional in the spec, and per-language grammar builds are a portability
and packaging burden that isn't worth it for what a regex boundary detector
already gets right for RAG retrieval purposes: keeping a function or class
together in one chunk whenever it reasonably fits.
"""
import re
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.utils.tokenization import count_tokens

_C_STYLE_LANGUAGES = {
    "javascript", "typescript", "java", "csharp", "go", "rust",
    "kotlin", "swift", "c", "cpp", "php",
}

_PYTHON_BOUNDARY_RE = re.compile(r"^(def |class |async def )")

_C_STYLE_BOUNDARY_RE = re.compile(
    r"^(export\s+)?(default\s+)?(public\s+|private\s+|protected\s+|static\s+)*"
    r"(async\s+)?(function\b|class\b|interface\b|struct\b|func\b|fn\b|enum\b)"
)
_C_STYLE_ARROW_RE = re.compile(r"^(export\s+)?(const|let|var)\s+\w+\s*=\s*(async\s*)?\(")

_MARKDOWN_BOUNDARY_RE = re.compile(r"^#{1,6}\s")

_MAX_BOUNDARY_INDENT = 2  # only treat near-top-level declarations as chunk boundaries


@dataclass
class CodeChunk:
    file_path: str
    language: str | None
    content: str
    start_line: int  # 1-indexed, inclusive
    end_line: int  # 1-indexed, inclusive
    chunk_index: int
    token_count: int


def _python_boundaries(lines: list[str]) -> list[int]:
    return [i for i, line in enumerate(lines) if _PYTHON_BOUNDARY_RE.match(line)]


def _c_style_boundaries(lines: list[str]) -> list[int]:
    boundaries = []
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if indent > _MAX_BOUNDARY_INDENT:
            continue
        if _C_STYLE_BOUNDARY_RE.match(stripped) or _C_STYLE_ARROW_RE.match(stripped):
            boundaries.append(i)
    return boundaries


def _markdown_boundaries(lines: list[str]) -> list[int]:
    return [i for i, line in enumerate(lines) if _MARKDOWN_BOUNDARY_RE.match(line)]


def _boundaries_for_language(lines: list[str], language: str | None) -> list[int]:
    if language == "python":
        return _python_boundaries(lines)
    if language in _C_STYLE_LANGUAGES:
        return _c_style_boundaries(lines)
    if language == "markdown":
        return _markdown_boundaries(lines)
    return []


def _split_into_blocks(lines: list[str], boundaries: list[int]) -> list[tuple[int, int]]:
    """Returns (start, end) 0-based half-open line ranges spanning the whole file."""
    if not boundaries:
        return [(0, len(lines))]

    blocks: list[tuple[int, int]] = []
    if boundaries[0] > 0:
        blocks.append((0, boundaries[0]))  # imports / module docstring / header before the first block

    for i, start in enumerate(boundaries):
        end = boundaries[i + 1] if i + 1 < len(boundaries) else len(lines)
        blocks.append((start, end))

    return blocks


def _sliding_window_split(
    lines: list[str], start: int, end: int, max_tokens: int, overlap_tokens: int
) -> list[tuple[int, int]]:
    """Token-aware sliding window over lines[start:end], with trailing overlap between windows."""
    if end <= start:
        return []

    line_tokens = [count_tokens(lines[i]) for i in range(start, end)]
    blocks: list[tuple[int, int]] = []
    i = start
    while i < end:
        tokens = 0
        j = i
        while j < end and (tokens + line_tokens[j - start] <= max_tokens or j == i):
            tokens += line_tokens[j - start]
            j += 1
        blocks.append((i, j))
        if j >= end:
            break

        back_tokens = 0
        k = j
        while k > i and back_tokens < overlap_tokens:
            k -= 1
            back_tokens += line_tokens[k - start]
        i = max(k, i + 1)  # always make forward progress even if overlap would stall it

    return blocks


def chunk_text(content: str, file_path: str, language: str | None) -> list[CodeChunk]:
    """Splits raw file content into CodeChunks. Returns [] for blank/whitespace-only content."""
    if not content or not content.strip():
        return []

    lines = content.splitlines()
    boundaries = _boundaries_for_language(lines, language)
    blocks = _split_into_blocks(lines, boundaries)

    final_ranges: list[tuple[int, int]] = []
    for start, end in blocks:
        block_tokens = count_tokens("\n".join(lines[start:end]))
        if block_tokens <= settings.MAX_CHUNK_SIZE_TOKENS:
            final_ranges.append((start, end))
        else:
            final_ranges.extend(
                _sliding_window_split(
                    lines, start, end, settings.MAX_CHUNK_SIZE_TOKENS, settings.CHUNK_OVERLAP_TOKENS
                )
            )

    chunks: list[CodeChunk] = []
    for start, end in final_ranges:
        text = "\n".join(lines[start:end])
        if not text.strip():
            continue
        chunks.append(
            CodeChunk(
                file_path=file_path,
                language=language,
                content=text,
                start_line=start + 1,
                end_line=end,
                chunk_index=len(chunks),
                token_count=count_tokens(text),
            )
        )

    return chunks


def chunk_repository_file(absolute_path: Path, relative_path: Path, language: str | None) -> list[CodeChunk]:
    """Reads a file from disk and chunks it, tolerating non-UTF-8 encodings."""
    try:
        content = absolute_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = absolute_path.read_text(encoding="latin-1", errors="replace")

    return chunk_text(content, str(relative_path).replace("\\", "/"), language)
