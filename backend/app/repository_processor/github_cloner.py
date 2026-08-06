"""Clones a GitHub repository URL using a shallow (depth=1) clone."""
from pathlib import Path

from git import GitCommandError, Repo

from app.core.exceptions import ExternalServiceException
from app.core.logging import get_logger

logger = get_logger(__name__)


def clone_repository(source_url: str, destination: Path) -> str:
    """Shallow-clones source_url into destination and returns the checked-out branch name.

    Assumes source_url has already passed app.utils.validators.validate_github_url —
    this function does not itself restrict scheme/host.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        repo = Repo.clone_from(source_url, destination, depth=1, single_branch=True)
    except GitCommandError as exc:
        logger.warning("git clone failed for %s: %s", source_url, exc)
        raise ExternalServiceException(f"Failed to clone repository: {source_url}")

    try:
        branch_name = repo.active_branch.name
    except TypeError:
        # Detached HEAD can happen for shallow clones of certain refs.
        branch_name = "HEAD"

    repo.close()
    return branch_name
