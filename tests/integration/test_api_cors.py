from __future__ import annotations

from fastapi.testclient import TestClient

from frostfire.app import create_app
from frostfire.config.settings import Settings


def test_cors_enabled_returns_allow_origin_for_allowed_origin() -> None:
    app = create_app(
        Settings(
            _env_file=None,
            API_TOKEN="test-token",
            CORS_ENABLED=True,
            CORS_ALLOWED_ORIGINS="https://example.com, https://other.test",
        )
    )

    with TestClient(app) as client:
        response = client.options(
            "/health",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://example.com"
