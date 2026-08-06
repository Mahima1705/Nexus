import pytest
from fastapi import UploadFile
from io import BytesIO

from app.core.exceptions import BadRequestException
from app.utils.validators import validate_github_url, validate_zip_upload_filename


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://github.com/octocat/Hello-World", ("octocat", "Hello-World")),
        ("https://github.com/octocat/Hello-World.git", ("octocat", "Hello-World")),
        ("https://github.com/octocat/Hello-World/", ("octocat", "Hello-World")),
    ],
)
def test_validate_github_url_accepts_well_formed_urls(url: str, expected: tuple[str, str]) -> None:
    assert validate_github_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/octocat/Hello-World",  # not https
        "https://evil.com/octocat/Hello-World",  # wrong host
        "git://github.com/octocat/Hello-World",  # wrong scheme
        "https://github.com.evil.com/octocat/Hello-World",  # host confusion
        "file:///etc/passwd",
        "https://github.com/octocat",  # missing repo segment
        "not-a-url",
        "https://github.com/../../etc/passwd",
    ],
)
def test_validate_github_url_rejects_unsafe_or_malformed_urls(url: str) -> None:
    with pytest.raises(BadRequestException):
        validate_github_url(url)


def test_validate_zip_upload_filename_accepts_zip() -> None:
    upload = UploadFile(filename="my-repo.zip", file=BytesIO(b""))
    validate_zip_upload_filename(upload)  # should not raise


def test_validate_zip_upload_filename_rejects_non_zip() -> None:
    upload = UploadFile(filename="my-repo.tar.gz", file=BytesIO(b""))
    with pytest.raises(BadRequestException):
        validate_zip_upload_filename(upload)
