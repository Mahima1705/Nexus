"""Filesystem helpers shared by the repository processor."""
import hashlib
from pathlib import Path


def safe_join(base: Path, *parts: str) -> Path:
    """Joins path parts onto base, raising ValueError if the result escapes base.

    This is the core defense against path traversal (e.g. "../../etc/passwd" or an
    absolute path) when resolving a file path supplied by the client or found inside
    an untrusted ZIP archive.
    """
    base = base.resolve()
    candidate = base.joinpath(*parts).resolve()
    try:
        candidate.relative_to(base)
    except ValueError:
        raise ValueError(f"Path traversal attempt detected: {parts!r}")
    return candidate


def compute_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def directory_size_bytes(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
