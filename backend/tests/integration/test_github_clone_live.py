"""Live network test: clones a real, tiny public GitHub repo end-to-end.

Skipped automatically when there's no network access (e.g. offline CI runners).
Everything else in the suite runs fully offline against SQLite — this is the
one deliberate exception, because "does GitPython actually clone a real repo"
can't be verified any other way.
"""
import shutil
import socket
from pathlib import Path

import pytest

from app.core.exceptions import ExternalServiceException
from app.repository_processor.github_cloner import clone_repository


def _network_available() -> bool:
    try:
        socket.create_connection(("github.com", 443), timeout=3).close()
        return True
    except OSError:
        return False


pytestmark = pytest.mark.skipif(not _network_available(), reason="No network access to github.com")


def test_clone_repository_live(tmp_path: Path) -> None:
    destination = tmp_path / "hello-world"

    branch = clone_repository("https://github.com/octocat/Hello-World", destination)

    assert branch
    extracted_files = [p for p in destination.rglob("*") if p.is_file() and ".git" not in p.parts]
    assert len(extracted_files) > 0

    shutil.rmtree(destination, ignore_errors=True)


def test_clone_repository_live_wraps_git_failure_for_nonexistent_repo(tmp_path: Path) -> None:
    """A real `git clone` against a repo that doesn't exist actually fails with
    GitCommandError — proving our except clause catches the type git really
    raises, not just the type we assumed it would.
    """
    destination = tmp_path / "does-not-exist"

    with pytest.raises(ExternalServiceException):
        clone_repository("https://github.com/octocat/this-repo-does-not-exist-xyz123", destination)
