from fastapi.testclient import TestClient

from frostfire.app import create_app


def test_health_returns_ok() -> None:
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "frostfire-backend"
    assert payload["version"] == "0.1.0"
