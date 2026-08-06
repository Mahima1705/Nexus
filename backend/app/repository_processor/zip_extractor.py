"""Safe ZIP extraction: rejects path traversal, symlinks, and oversized archives."""
import shutil
import stat
import zipfile
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import BadRequestException
from app.utils.file_utils import safe_join

MAX_MEMBER_COUNT = 50_000


def extract_zip_safely(zip_path: Path, destination: Path) -> None:
    """Extracts zip_path into destination, guarding against zip-slip and zip bombs.

    Every member's resolved destination path is verified to stay within
    `destination` (zip-slip protection), symlink entries are rejected outright, and
    both the entry count and total uncompressed size are capped before any bytes
    are written (zip-bomb protection).
    """
    destination.mkdir(parents=True, exist_ok=True)

    if not zipfile.is_zipfile(zip_path):
        raise BadRequestException("Uploaded file is not a valid ZIP archive.")

    max_extracted_bytes = settings.MAX_REPO_SIZE_MB * 1024 * 1024

    with zipfile.ZipFile(zip_path) as archive:
        members = archive.infolist()

        if len(members) > MAX_MEMBER_COUNT:
            raise BadRequestException(f"ZIP archive contains too many entries (max {MAX_MEMBER_COUNT}).")

        total_uncompressed = sum(member.file_size for member in members)
        if total_uncompressed > max_extracted_bytes:
            raise BadRequestException(
                f"ZIP archive would extract to more than {settings.MAX_REPO_SIZE_MB}MB."
            )

        for member in members:
            mode = (member.external_attr >> 16) & 0xFFFF
            if mode and stat.S_ISLNK(mode):
                raise BadRequestException(f"ZIP archive contains a symlink ({member.filename}); rejected.")

            try:
                target_path = safe_join(destination, member.filename)
            except ValueError:
                raise BadRequestException(
                    f"ZIP archive contains an unsafe path ({member.filename}); rejected."
                )

            if member.is_dir():
                target_path.mkdir(parents=True, exist_ok=True)
                continue

            target_path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target_path.open("wb") as target:
                shutil.copyfileobj(source, target, length=1024 * 1024)
