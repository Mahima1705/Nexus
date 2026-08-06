import io
import zipfile

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.asyncio


def _make_test_zip_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
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


async def test_search_returns_structured_response(client: TestClient) -> None:
    token, repository_id = _register_login_and_ready_repo(client, "searcher@nexus.ai")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        f"/api/v1/repositories/{repository_id}/search",
        headers=headers,
        json={"query": "where should I add Google login?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "relevant_files" in body
    assert "explanation" in body
    assert "reasoning" in body


async def test_search_requires_auth(client: TestClient) -> None:
    response = client.post(
        "/api/v1/repositories/00000000-0000-0000-0000-000000000000/search", json={"query": "anything"}
    )
    assert response.status_code == 401


async def test_search_rejects_empty_query(client: TestClient) -> None:
    token, repository_id = _register_login_and_ready_repo(client, "emptysearcher@nexus.ai")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(f"/api/v1/repositories/{repository_id}/search", headers=headers, json={"query": ""})
    assert response.status_code == 422
