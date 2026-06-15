from __future__ import annotations

from fastapi.testclient import TestClient

from frostfire.app import create_app
from frostfire.config.settings import Settings


class FakeDeviceService:
    def __init__(self, ready: bool, *, error: str | None = None) -> None:
        self.ready = ready
        self.error = error

    async def check_readiness(self) -> dict[str, object]:
        if self.ready:
            return {"ready": True, "esp32": {"online": True}}
        return {"ready": False, "esp32": {"online": False, "error": self.error}}


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        API_TOKEN="test-token",
    )


def test_health_returns_ok() -> None:
    app = create_app(_settings())
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "frostfire-backend"


def test_ready_when_esp32_online() -> None:
    app = create_app(_settings(), device_service=FakeDeviceService(ready=True))

    with TestClient(app) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ready"] is True
    assert payload["esp32"]["online"] is True


def test_ready_when_esp32_offline() -> None:
    app = create_app(
        _settings(),
        device_service=FakeDeviceService(ready=False, error="device unreachable"),
    )

    with TestClient(app) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ready"] is False
    assert payload["esp32"]["online"] is False
    assert payload["esp32"]["error"] == "device unreachable"
