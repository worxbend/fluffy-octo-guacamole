from __future__ import annotations

import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

from frostfire.app import create_app
from frostfire.application.power_service import PowerService
from frostfire.application.safety_policy import SafetyPolicy
from frostfire.config.settings import Settings
from frostfire.domain.enums import PowerAction


class FakeEsp32Client:
    def __init__(self) -> None:
        self.calls: list[int] = []
        self.started = asyncio.Event()
        self.allow = asyncio.Event()
        self.allow.clear()

    async def pulse_relay(self, duration_ms: int) -> dict[str, object]:
        self.calls.append(duration_ms)
        self.started.set()
        await self.allow.wait()
        return {
            "accepted": True,
            "duration_ms": duration_ms,
            "message": "relay pulsed",
        }

    async def health(self) -> dict[str, object]:
        raise RuntimeError("not used in this test")

    async def status(self) -> dict[str, object]:
        raise RuntimeError("not used in this test")

    async def close(self) -> None:
        return None


class FakeStatusService:
    async def check_readiness(self) -> dict[str, object]:
        return {"ready": True, "esp32": {"online": True}}

    async def get_status(self):
        return {
            "online": True,
            "device_name": "frostfire-esp32",
            "ip_address": "192.168.1.50",
            "firmware_version": "0.1.0",
            "relay_state": "idle",
            "uptime_seconds": 1,
            "rssi": -55,
        }


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        API_TOKEN="test-token",
        MIN_COMMAND_INTERVAL_SECONDS=0.0,
        COMMAND_LOCK_TIMEOUT_SECONDS=0.05,
    )


def _app_with_fake_power_service(esp32_client: FakeEsp32Client) -> object:
    policy = SafetyPolicy(
        min_command_interval_seconds=0.0,
        command_lock_timeout_seconds=0.05,
    )
    power_service = PowerService(
        esp32_client=esp32_client,
        safety_policy=policy,
        power_press_duration_ms=500,
        force_off_press_duration_ms=5000,
    )
    app_settings = _settings()
    fake_device_service = FakeStatusService()
    app = create_app(
        app_settings,
        power_service=power_service,
        device_service=fake_device_service,
    )
    app.state.settings = app_settings
    app.state.power_service = power_service
    app.state.device_service = fake_device_service
    return app


def test_power_press_requires_authentication() -> None:
    app = _app_with_fake_power_service(FakeEsp32Client())
    with TestClient(app) as client:
        response = client.post("/api/v1/power/press")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_power_press_rejects_invalid_token() -> None:
    app = _app_with_fake_power_service(FakeEsp32Client())
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/power/press",
            headers={"Authorization": "Bearer bad-token"},
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_power_press_with_valid_token_executes() -> None:
    fake_esp32 = FakeEsp32Client()
    fake_esp32.allow.set()
    app = _app_with_fake_power_service(fake_esp32)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/power/press",
            headers={"Authorization": "Bearer test-token"},
        )
    payload = response.json()
    assert response.status_code == 200
    assert payload["action"] == PowerAction.PRESS.value
    assert payload["accepted"] is True
    assert fake_esp32.calls == [500]


def test_force_off_requires_confirmation() -> None:
    app = _app_with_fake_power_service(FakeEsp32Client())
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/power/force-off",
            headers={"Authorization": "Bearer test-token"},
            json={},
        )
    payload = response.json()
    assert response.status_code == 422
    assert payload["error"]["code"] == "unsafe_command"


@pytest.mark.asyncio
async def test_concurrent_power_commands() -> None:
    fake_esp32 = FakeEsp32Client()
    app = _app_with_fake_power_service(fake_esp32)

    transport = httpx.ASGITransport(app=app)
    headers = {"Authorization": "Bearer test-token"}

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        first = asyncio.create_task(
            client.post("/api/v1/power/press", headers=headers),
        )
        await fake_esp32.started.wait()
        second = asyncio.create_task(
            client.post("/api/v1/power/press", headers=headers),
        )

        second_response = await second
        assert second_response.status_code == 409
        assert second_response.json()["error"]["code"] == "command_in_progress"

        fake_esp32.allow.set()
        first_response = await first
        assert first_response.status_code == 200
