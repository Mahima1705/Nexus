import io
import zipfile

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.asyncio


def _make_test_zip_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("README.md", "# Demo")
        archive.writestr("src/main.py", "def main():\n    pass\n")
    buffer.seek(0)
    return buffer.read()


def _register_login_and_ready_repo(client: TestClient, email: str) -> tuple[str, str]:
    client.post("/api/v1/auth/register", json={"email": email, "password": "Str0ngPass"})
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "Str0ngPass"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/api/v1/repositories/upload",
        headers=headers,
        files={"file": ("demo.zip", _make_test_zip_bytes(), "application/zip")},
    )
    return token, created.json()["id"]


async def test_generate_folder_structure_documentation(client: TestClient) -> None:
    token, repository_id = _register_login_and_ready_repo(client, "docwriter@nexus.ai")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        f"/api/v1/docs/repositories/{repository_id}/generate",
        headers=headers,
        json={"doc_type": "folder_structure"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["doc_type"] == "folder_structure"
    assert "README.md" in body["content"]


async def test_generate_readme_documentation(client: TestClient) -> None:
    token, repository_id = _register_login_and_ready_repo(client, "readmewriter@nexus.ai")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        f"/api/v1/docs/repositories/{repository_id}/generate", headers=headers, json={"doc_type": "readme"}
    )

    assert response.status_code == 201
    assert response.json()["doc_type"] == "readme"
    assert response.json()["content"]


async def test_generate_documentation_requires_auth(client: TestClient) -> None:
    response = client.post(
        "/api/v1/docs/repositories/00000000-0000-0000-0000-000000000000/generate",
        json={"doc_type": "readme"},
    )
    assert response.status_code == 401


async def test_generate_documentation_rejects_invalid_doc_type(client: TestClient) -> None:
    token, repository_id = _register_login_and_ready_repo(client, "baddoctype@nexus.ai")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        f"/api/v1/docs/repositories/{repository_id}/generate",
        headers=headers,
        json={"doc_type": "not_a_real_type"},
    )
    assert response.status_code == 422
