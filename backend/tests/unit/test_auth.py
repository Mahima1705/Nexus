import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.asyncio


async def test_register_returns_user_without_password(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "alice@nexus.ai", "password": "Str0ngPass", "full_name": "Alice"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "alice@nexus.ai"
    assert "password" not in body
    assert "hashed_password" not in body


async def test_register_duplicate_email_returns_409(client: TestClient) -> None:
    payload = {"email": "bob@nexus.ai", "password": "Str0ngPass"}
    first = client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201

    second = client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "CONFLICT"


async def test_register_weak_password_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register", json={"email": "weak@nexus.ai", "password": "onlyletters"}
    )
    assert response.status_code == 422


async def test_login_with_correct_credentials_returns_tokens(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json={"email": "carol@nexus.ai", "password": "Str0ngPass"})

    response = client.post(
        "/api/v1/auth/login", json={"email": "carol@nexus.ai", "password": "Str0ngPass"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]


async def test_login_with_wrong_password_returns_401(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json={"email": "dave@nexus.ai", "password": "Str0ngPass"})

    response = client.post(
        "/api/v1/auth/login", json={"email": "dave@nexus.ai", "password": "WrongPass1"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


async def test_me_requires_bearer_token(client: TestClient) -> None:
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401


async def test_me_returns_current_user_with_valid_access_token(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json={"email": "erin@nexus.ai", "password": "Str0ngPass"})
    login = client.post("/api/v1/auth/login", json={"email": "erin@nexus.ai", "password": "Str0ngPass"})
    access_token = login.json()["access_token"]

    response = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "erin@nexus.ai"


async def test_refresh_rotates_token_and_old_one_becomes_invalid(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json={"email": "frank@nexus.ai", "password": "Str0ngPass"})
    login = client.post("/api/v1/auth/login", json={"email": "frank@nexus.ai", "password": "Str0ngPass"})
    old_refresh_token = login.json()["refresh_token"]

    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh_token})
    assert refreshed.status_code == 200
    new_tokens = refreshed.json()
    assert new_tokens["refresh_token"] != old_refresh_token

    reused = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh_token})
    assert reused.status_code == 401


async def test_logout_revokes_refresh_token(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json={"email": "grace@nexus.ai", "password": "Str0ngPass"})
    login = client.post("/api/v1/auth/login", json={"email": "grace@nexus.ai", "password": "Str0ngPass"})
    refresh_token = login.json()["refresh_token"]

    logout = client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert logout.status_code == 204

    attempted_refresh = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert attempted_refresh.status_code == 401
