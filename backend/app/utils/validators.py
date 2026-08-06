"""Input validators used at API boundaries (uploads, GitHub URLs)."""
import re

from fastapi import UploadFile

from app.core.exceptions import BadRequestException

# Deliberately anchors scheme to https and host to the literal string "github.com" —
# accepting an arbitrary scheme/host here (git://, file://, an internal hostname)
# would let a client make this server clone from anywhere, including internal
# network addresses (SSRF).
_GITHUB_URL_RE = re.compile(
    r"^https://github\.com/(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)


def validate_github_url(url: str) -> tuple[str, str]:
    """Validates a GitHub repository URL and returns (owner, repo).

    Raises BadRequestException if the URL is not a well-formed
    https://github.com/<owner>/<repo> URL.
    """
    match = _GITHUB_URL_RE.match(url.strip())
    if not match:
        raise BadRequestException(
            "Invalid GitHub repository URL. Expected format: https://github.com/<owner>/<repo>"
        )
    return match.group("owner"), match.group("repo")


def validate_zip_upload_filename(upload: UploadFile) -> None:
    """Fast, cheap pre-check on the filename. The authoritative check is
    zipfile.is_zipfile() performed during extraction — this only exists to reject
    obviously-wrong uploads before we spend time writing them to disk.
    """
    filename = upload.filename or ""
    if not filename.lower().endswith(".zip"):
        raise BadRequestException("Only .zip file uploads are supported.")
