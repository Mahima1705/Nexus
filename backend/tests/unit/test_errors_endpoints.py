import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.asyncio


def _register_and_login(client: TestClient, email: str) -> str:
    client.post("/api/v1/auth/register", json={"email": email, "password": "Str0ngPass"})
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "Str0ngPass"})
    return login.json()["access_token"]


async def test_analyze_error_without_repository(client: TestClient) -> None:
    token = _register_and_login(client, "erroranalyst@nexus.ai")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/v1/errors/analyze",
        headers=headers,
        json={"error_text": "Traceback (most recent call last):\nNullPointerException"},
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {
        "explanation",
        "likely_cause",
        "relevant_files",
        "debugging_suggestions",
        "possible_fixes",
    }


async def test_analyze_error_requires_auth(client: TestClient) -> None:
    response = client.post("/api/v1/errors/analyze", json={"error_text": "some error"})
    assert response.status_code == 401


async def test_analyze_error_rejects_empty_text(client: TestClient) -> None:
    token = _register_and_login(client, "emptyerroranalyst@nexus.ai")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/api/v1/errors/analyze", headers=headers, json={"error_text": ""})
    assert response.status_code == 422


async def test_analyze_error_with_repository_not_owned_returns_403(client: TestClient) -> None:
    token_a = _register_and_login(client, "erroranalystowner@nexus.ai")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    import io
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("main.py", "def foo(): pass\n")
    buffer.seek(0)

    created = client.post(
        "/api/v1/repositories/upload",
        headers=headers_a,
        files={"file": ("demo.zip", buffer.read(), "application/zip")},
    )
    repository_id = created.json()["id"]

    token_b = _register_and_login(client, "erroranalystintruder@nexus.ai")
    response = client.post(
        "/api/v1/errors/analyze",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"error_text": "some error", "repository_id": repository_id},
    )
    assert response.status_code == 403
