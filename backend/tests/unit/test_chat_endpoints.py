import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.asyncio


def _make_test_zip_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("README.md", "# Demo Repo")
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
    repository_id = created.json()["id"]

    # The POST response body is a snapshot taken before the background task runs
    # (which has already completed by now, since TestClient blocks on it) — fetch
    # fresh state rather than trusting that snapshot.
    fetched = client.get(f"/api/v1/repositories/{repository_id}", headers=headers)
    assert fetched.json()["status"] == "ready"
    return token, repository_id


async def test_chat_flow_end_to_end(client: TestClient) -> None:
    token, repository_id = _register_login_and_ready_repo(client, "chatuser@nexus.ai")
    headers = {"Authorization": f"Bearer {token}"}

    session_resp = client.post(
        f"/api/v1/repositories/{repository_id}/sessions", headers=headers, json={"title": "Q&A"}
    )
    assert session_resp.status_code == 201
    session_id = session_resp.json()["id"]

    message_resp = client.post(
        f"/api/v1/sessions/{session_id}/messages", headers=headers, json={"content": "How does this work?"}
    )
    assert message_resp.status_code == 201
    body = message_resp.json()
    assert body["role"] == "assistant"
    assert "Fake answer" in body["content"]

    messages_resp = client.get(f"/api/v1/sessions/{session_id}/messages", headers=headers)
    assert messages_resp.status_code == 200
    assert len(messages_resp.json()) == 2
    assert messages_resp.json()[0]["role"] == "user"

    sessions_resp = client.get(f"/api/v1/repositories/{repository_id}/sessions", headers=headers)
    assert sessions_resp.status_code == 200
    assert len(sessions_resp.json()) == 1


async def test_chat_stream_end_to_end(client: TestClient) -> None:
    token, repository_id = _register_login_and_ready_repo(client, "streamuser@nexus.ai")
    headers = {"Authorization": f"Bearer {token}"}

    session_resp = client.post(f"/api/v1/repositories/{repository_id}/sessions", headers=headers, json={})
    session_id = session_resp.json()["id"]

    with client.stream(
        "POST",
        f"/api/v1/sessions/{session_id}/messages/stream",
        headers=headers,
        json={"content": "How does this work?"},
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")

        events = []
        for line in response.iter_lines():
            if line.startswith("data:"):
                events.append(json.loads(line[len("data:") :].strip()))

    assert events[-1]["type"] == "done"
    assert "".join(e["content"] for e in events if e["type"] == "chunk").strip().startswith("Fake answer")
    assert events[-1]["message"]["role"] == "assistant"

    messages_resp = client.get(f"/api/v1/sessions/{session_id}/messages", headers=headers)
    assert len(messages_resp.json()) == 2


async def test_chat_requires_auth(client: TestClient) -> None:
    response = client.get("/api/v1/repositories/00000000-0000-0000-0000-000000000000/sessions")
    assert response.status_code == 401


async def test_cannot_access_another_users_session(client: TestClient) -> None:
    token_a, repository_id = _register_login_and_ready_repo(client, "chatowner@nexus.ai")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    session_resp = client.post(f"/api/v1/repositories/{repository_id}/sessions", headers=headers_a, json={})
    session_id = session_resp.json()["id"]

    client.post("/api/v1/auth/register", json={"email": "intruder@nexus.ai", "password": "Str0ngPass"})
    login_b = client.post("/api/v1/auth/login", json={"email": "intruder@nexus.ai", "password": "Str0ngPass"})
    token_b = login_b.json()["access_token"]

    response = client.get(
        f"/api/v1/sessions/{session_id}/messages", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert response.status_code == 403
