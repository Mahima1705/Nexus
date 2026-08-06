from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_returns_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "Nexus"


def test_root_returns_docs_link() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "docs" in response.json()


def test_unknown_route_returns_404() -> None:
    response = client.get("/does-not-exist")
    assert response.status_code == 404
