import io
import shutil
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _cleanup_storage():
    """Repository upload/clone writes real files under backend/storage/ — clean up after each test."""
    yield
    for base in (Path(settings.REPOS_DIR), Path(settings.UPLOAD_DIR)):
        if not base.exists():
            continue
        for child in base.iterdir():
            if child.name == ".gitkeep":
                continue
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            else:
                child.unlink(missing_ok=True)


def _make_test_zip_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("README.md", "# Demo Repo")
        archive.writestr("src/main.py", "def main():\n    pass\n")
        archive.writestr("node_modules/pkg/index.js", "module.exports = {}")
    buffer.seek(0)
    return buffer.read()


def _register_and_login(client: TestClient, email: str) -> str:
    client.post("/api/v1/auth/register", json={"email": email, "password": "Str0ngPass"})
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "Str0ngPass"})
    return login.json()["access_token"]


async def test_repository_endpoints_require_auth(client: TestClient) -> None:
    assert client.get("/api/v1/repositories").status_code == 401
    assert (
        client.post(
            "/api/v1/repositories/github", json={"source_url": "https://github.com/octocat/Hello-World"}
        ).status_code
        == 401
    )


async def test_create_from_github_rejects_invalid_url(client: TestClient) -> None:
    token = _register_and_login(client, "gh@nexus.ai")
    response = client.post(
        "/api/v1/repositories/github",
        json={"source_url": "https://evil.com/octocat/Hello-World"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400


async def test_upload_zip_creates_and_indexes_repository(client: TestClient) -> None:
    token = _register_and_login(client, "uploader@nexus.ai")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/v1/repositories/upload",
        headers=headers,
        files={"file": ("demo-repo.zip", _make_test_zip_bytes(), "application/zip")},
        data={"name": "demo-repo"},
    )
    assert response.status_code == 201
    repository_id = response.json()["id"]

    # TestClient's post() blocks until the ASGI background task has fully run.
    fetched = client.get(f"/api/v1/repositories/{repository_id}", headers=headers)
    assert fetched.status_code == 200
    body = fetched.json()
    assert body["status"] == "ready"
    assert body["total_files"] == 2  # README.md + src/main.py; node_modules/* is ignored
    assert body["total_chunks"] == 2  # each of the two files is small enough to be a single chunk


async def test_upload_rejects_non_zip_file(client: TestClient) -> None:
    token = _register_and_login(client, "badupload@nexus.ai")
    response = client.post(
        "/api/v1/repositories/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400


async def test_users_only_see_their_own_repositories(client: TestClient) -> None:
    token_a = _register_and_login(client, "usera@nexus.ai")
    token_b = _register_and_login(client, "userb@nexus.ai")

    client.post(
        "/api/v1/repositories/upload",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"file": ("repo-a.zip", _make_test_zip_bytes(), "application/zip")},
    )

    response_b = client.get("/api/v1/repositories", headers={"Authorization": f"Bearer {token_b}"})
    assert response_b.status_code == 200
    assert response_b.json() == []

    response_a = client.get("/api/v1/repositories", headers={"Authorization": f"Bearer {token_a}"})
    assert len(response_a.json()) == 1


async def test_get_repository_not_owned_returns_403(client: TestClient) -> None:
    token_a = _register_and_login(client, "ownera@nexus.ai")
    token_b = _register_and_login(client, "ownerb@nexus.ai")

    created = client.post(
        "/api/v1/repositories/upload",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"file": ("repo-a.zip", _make_test_zip_bytes(), "application/zip")},
    )
    repository_id = created.json()["id"]

    response = client.get(
        f"/api/v1/repositories/{repository_id}", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert response.status_code == 403


async def test_delete_repository_removes_it(client: TestClient) -> None:
    token = _register_and_login(client, "deleter@nexus.ai")
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post(
        "/api/v1/repositories/upload",
        headers=headers,
        files={"file": ("to-delete.zip", _make_test_zip_bytes(), "application/zip")},
    )
    repository_id = created.json()["id"]

    delete_response = client.delete(f"/api/v1/repositories/{repository_id}", headers=headers)
    assert delete_response.status_code == 204

    get_response = client.get(f"/api/v1/repositories/{repository_id}", headers=headers)
    assert get_response.status_code == 404
