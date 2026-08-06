from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.repository_processor import github_cloner


def test_clone_repository_falls_back_to_head_on_detached_head(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake_repo = MagicMock()
    type(fake_repo).active_branch = property(lambda self: (_ for _ in ()).throw(TypeError("detached HEAD")))

    monkeypatch.setattr(github_cloner.Repo, "clone_from", lambda *a, **k: fake_repo)

    branch = github_cloner.clone_repository("https://github.com/owner/repo", tmp_path / "dest")

    assert branch == "HEAD"
    fake_repo.close.assert_called_once()
