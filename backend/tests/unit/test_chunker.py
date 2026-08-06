from pathlib import Path
from textwrap import dedent

import pytest

from app.core.config import settings
from app.repository_processor.chunker import chunk_repository_file, chunk_text


def test_chunk_text_empty_content_returns_no_chunks() -> None:
    assert chunk_text("", "empty.py", "python") == []
    assert chunk_text("   \n\n  ", "blank.py", "python") == []


def test_chunk_text_python_splits_at_top_level_def_and_class() -> None:
    content = dedent(
        '''\
        import os

        def first_function():
            return 1

        class MyClass:
            def method(self):
                return 2

        def second_function():
            return 3
        '''
    )

    chunks = chunk_text(content, "app/module.py", "python")

    assert len(chunks) == 4
    assert [c.chunk_index for c in chunks] == [0, 1, 2, 3]
    assert "import os" in chunks[0].content
    assert chunks[1].content.startswith("def first_function")
    assert chunks[2].content.startswith("class MyClass")
    assert "def method" in chunks[2].content  # nested method stays with its class
    assert chunks[3].content.startswith("def second_function")


def test_chunk_text_line_numbers_reconstruct_the_source() -> None:
    content = "line1\nline2\nline3\nline4\n"
    chunks = chunk_text(content, "plain.txt", None)

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.start_line == 1
    assert chunk.end_line == 4
    assert chunk.content.splitlines() == ["line1", "line2", "line3", "line4"]


def test_chunk_text_javascript_detects_function_class_and_arrow_boundaries() -> None:
    content = dedent(
        """\
        import React from 'react';

        function Greeter() {
          return 'hi';
        }

        export class Widget {
          render() {}
        }

        const handler = async (req, res) => {
          return res.send('ok');
        };
        """
    )

    chunks = chunk_text(content, "src/app.js", "javascript")

    assert len(chunks) == 4
    assert chunks[1].content.startswith("function Greeter")
    assert chunks[2].content.startswith("export class Widget")
    assert chunks[3].content.startswith("const handler")


def test_chunk_text_markdown_splits_at_headings() -> None:
    content = dedent(
        """\
        # Title

        Intro paragraph.

        ## Installation

        Run pip install.

        ## Usage

        Run the app.
        """
    )

    chunks = chunk_text(content, "README.md", "markdown")

    assert len(chunks) == 3
    assert chunks[0].content.startswith("# Title")
    assert chunks[1].content.startswith("## Installation")
    assert chunks[2].content.startswith("## Usage")


def test_chunk_text_unknown_language_falls_back_to_single_chunk_when_small() -> None:
    content = '{"key": "value"}'
    chunks = chunk_text(content, "config.json", "json")
    assert len(chunks) == 1
    assert chunks[0].content == content


def test_chunk_text_splits_oversized_block_with_overlap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "MAX_CHUNK_SIZE_TOKENS", 15)
    monkeypatch.setattr(settings, "CHUNK_OVERLAP_TOKENS", 5)

    lines = [f"line number {i} with a few words here" for i in range(30)]
    content = "\n".join(lines)

    chunks = chunk_text(content, "big.txt", None)

    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.token_count <= 15 or chunk.start_line == chunk.end_line

    # Consecutive chunks should overlap or at least be contiguous, never leave a gap.
    for earlier, later in zip(chunks, chunks[1:]):
        assert later.start_line <= earlier.end_line + 1

    # chunk_index is sequential starting at 0
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_chunk_text_oversized_python_function_is_sub_split(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "MAX_CHUNK_SIZE_TOKENS", 30)
    monkeypatch.setattr(settings, "CHUNK_OVERLAP_TOKENS", 5)

    body_lines = "\n".join(f"    value_{i} = {i}" for i in range(40))
    content = f"def huge_function():\n{body_lines}\n    return value_0\n"

    chunks = chunk_text(content, "big.py", "python")

    assert len(chunks) > 1
    assert chunks[0].content.startswith("def huge_function")


def test_chunk_repository_file_reads_and_chunks_from_disk(tmp_path: Path) -> None:
    file_path = tmp_path / "main.py"
    file_path.write_text("def foo():\n    return 1\n", encoding="utf-8")

    chunks = chunk_repository_file(file_path, Path("main.py"), "python")

    assert len(chunks) == 1
    assert chunks[0].file_path == "main.py"
    assert chunks[0].content.startswith("def foo")


def test_chunk_repository_file_tolerates_non_utf8_encoding(tmp_path: Path) -> None:
    file_path = tmp_path / "legacy.py"
    file_path.write_bytes("# café\ndef foo():\n    pass\n".encode("latin-1"))

    chunks = chunk_repository_file(file_path, Path("legacy.py"), "python")

    assert len(chunks) >= 1
