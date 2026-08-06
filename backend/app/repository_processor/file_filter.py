"""Decides which files in a cloned/extracted repository get recorded and indexed."""
from pathlib import Path
from typing import Iterator

from app.core.config import settings

_LANGUAGE_BY_EXTENSION: dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".java": "java",
    ".rb": "ruby",
    ".php": "php",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".rs": "rust",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".swift": "swift",
    ".md": "markdown",
    ".mdx": "markdown",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".sass": "sass",
    ".sql": "sql",
    ".sh": "shell",
    ".bash": "shell",
    ".xml": "xml",
    ".toml": "toml",
    ".ini": "ini",
    ".vue": "vue",
}

_BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".svg",
    ".pdf", ".zip", ".tar", ".gz", ".7z", ".rar",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".class", ".jar",
    ".mp3", ".mp4", ".mov", ".avi", ".wav",
    ".pyc", ".pyo",
    ".lock",
}


def is_binary_extension(path: Path) -> bool:
    return path.suffix.lower() in _BINARY_EXTENSIONS


def detect_language(path: Path) -> str | None:
    if path.name == "Dockerfile":
        return "dockerfile"
    return _LANGUAGE_BY_EXTENSION.get(path.suffix.lower())


def iter_repository_files(root: Path) -> Iterator[tuple[Path, Path]]:
    """Yields (absolute_path, relative_path) for every file worth recording.

    Ignored directories (node_modules, .git, dist, ...) are skipped by never
    descending into them, rather than filtering the full recursive listing
    afterwards — this keeps huge ignored trees like node_modules from being
    walked at all.
    """
    ignored = set(settings.IGNORED_DIRECTORIES)

    def _walk(directory: Path) -> Iterator[Path]:
        for entry in sorted(directory.iterdir(), key=lambda p: p.name):
            if entry.is_symlink():
                continue
            if entry.is_dir():
                if entry.name in ignored:
                    continue
                yield from _walk(entry)
            elif entry.is_file():
                yield entry

    for absolute_path in _walk(root):
        yield absolute_path, absolute_path.relative_to(root)
