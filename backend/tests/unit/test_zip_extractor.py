import zipfile
from pathlib import Path

import pytest

from app.core.config import settings
from app.core.exceptions import BadRequestException
from app.repository_processor.zip_extractor import extract_zip_safely


def _make_zip(tmp_path: Path, entries: dict[str, bytes], name: str = "archive.zip") -> Path:
    zip_path = tmp_path / name
    with zipfile.ZipFile(zip_path, "w") as archive:
        for filename, content in entries.items():
            archive.writestr(filename, content)
    return zip_path


def test_extract_zip_safely_extracts_normal_archive(tmp_path: Path) -> None:
    zip_path = _make_zip(
        tmp_path,
        {
            "README.md": b"# Hello",
            "src/main.py": b"print('hi')",
            "src/nested/util.py": b"def f(): pass",
        },
    )
    destination = tmp_path / "out"

    extract_zip_safely(zip_path, destination)

    assert (destination / "README.md").read_bytes() == b"# Hello"
    assert (destination / "src" / "main.py").read_bytes() == b"print('hi')"
    assert (destination / "src" / "nested" / "util.py").read_bytes() == b"def f(): pass"


def test_extract_zip_safely_rejects_path_traversal(tmp_path: Path) -> None:
    zip_path = _make_zip(tmp_path, {"../../evil.txt": b"pwned"})
    destination = tmp_path / "out"

    with pytest.raises(BadRequestException):
        extract_zip_safely(zip_path, destination)


def test_extract_zip_safely_rejects_absolute_path_member(tmp_path: Path) -> None:
    zip_path = _make_zip(tmp_path, {"/etc/passwd": b"pwned"}, name="abs.zip")
    destination = tmp_path / "out"

    with pytest.raises(BadRequestException):
        extract_zip_safely(zip_path, destination)


def test_extract_zip_safely_rejects_non_zip_file(tmp_path: Path) -> None:
    fake_zip = tmp_path / "not-a-zip.zip"
    fake_zip.write_bytes(b"this is not a zip file")

    with pytest.raises(BadRequestException):
        extract_zip_safely(fake_zip, tmp_path / "out")


def test_extract_zip_safely_rejects_oversized_archive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "MAX_REPO_SIZE_MB", 0)
    zip_path = _make_zip(tmp_path, {"big.txt": b"x" * 1024})

    with pytest.raises(BadRequestException):
        extract_zip_safely(zip_path, tmp_path / "out")


def test_extract_zip_safely_rejects_too_many_entries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import app.repository_processor.zip_extractor as zip_extractor_module

    monkeypatch.setattr(zip_extractor_module, "MAX_MEMBER_COUNT", 2)
    zip_path = _make_zip(tmp_path, {"a.txt": b"1", "b.txt": b"2", "c.txt": b"3"})

    with pytest.raises(BadRequestException):
        extract_zip_safely(zip_path, tmp_path / "out")
