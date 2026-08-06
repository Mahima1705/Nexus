import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.asyncio


def _register_and_login(client: TestClient, email: str) -> str:
    client.post("/api/v1/auth/register", json={"email": email, "password": "Str0ngPass"})
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "Str0ngPass"})
    return login.json()["access_token"]


async def test_review_snippet_returns_structured_result(client: TestClient) -> None:
    token = _register_and_login(client, "snippetreviewer@nexus.ai")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/v1/review/snippet",
        headers=headers,
        json={"source_code": "def foo():\n    pass", "language": "python"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["input_type"] == "snippet"
    assert set(body["review_result"].keys()) == {
        "bugs",
        "security_issues",
        "code_smells",
        "performance_suggestions",
        "best_practices",
    }


async def test_review_snippet_requires_auth(client: TestClient) -> None:
    response = client.post("/api/v1/review/snippet", json={"source_code": "def foo(): pass"})
    assert response.status_code == 401


async def test_review_snippet_rejects_empty_source(client: TestClient) -> None:
    token = _register_and_login(client, "emptyreviewer@nexus.ai")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/api/v1/review/snippet", headers=headers, json={"source_code": ""})
    assert response.status_code == 422


async def test_review_file_accepts_uploaded_source_file(client: TestClient) -> None:
    token = _register_and_login(client, "filereviewer@nexus.ai")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/v1/review/file",
        headers=headers,
        files={"file": ("main.py", b"def foo():\n    pass\n", "text/x-python")},
        data={"language": "python"},
    )

    assert response.status_code == 201
    assert response.json()["input_type"] == "file"
    assert response.json()["input_reference"] == "main.py"


async def test_review_file_rejects_oversized_upload(client: TestClient) -> None:
    token = _register_and_login(client, "hugereviewer@nexus.ai")
    headers = {"Authorization": f"Bearer {token}"}

    oversized_content = b"x" * (200 * 1024 + 1)
    response = client.post(
        "/api/v1/review/file",
        headers=headers,
        files={"file": ("huge.py", oversized_content, "text/x-python")},
    )

    assert response.status_code == 400
