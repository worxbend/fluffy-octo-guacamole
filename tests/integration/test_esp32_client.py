from __future__ import annotations

import httpx
import pytest

from frostfire.domain.errors import DeviceProtocolError, DeviceUnavailableError
from frostfire.infrastructure.esp32_client import Esp32Client


def _make_client(handler) -> httpx.AsyncClient:
    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(transport=transport, base_url="http://192.168.1.50")


@pytest.mark.asyncio
async def test_health_request_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/health"
        return httpx.Response(
            status_code=200,
            json={
                "status": "ok",
                "device": "frostfire-esp32",
                "firmware_version": "0.1.0",
            },
        )

    async with _make_client(handler) as http_client:
        esp32 = Esp32Client(base_url="http://192.168.1.50", client=http_client)
        result = await esp32.health()
        assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_status_request_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/status"
        return httpx.Response(
            status_code=200,
            json={
                "device": "frostfire-esp32",
                "firmware_version": "0.1.0",
                "relay_state": "idle",
                "uptime_seconds": 10,
                "rssi": -55,
            },
        )

    async with _make_client(handler) as http_client:
        esp32 = Esp32Client(base_url="http://192.168.1.50", client=http_client)
        result = await esp32.status()
        assert result["relay_state"] == "idle"


@pytest.mark.asyncio
async def test_pulse_request_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/relay/pulse"
        assert request.method == "POST"
        return httpx.Response(
            status_code=200,
            json={
                "accepted": True,
                "duration_ms": 500,
                "message": "relay pulsed",
            },
        )

    async with _make_client(handler) as http_client:
        esp32 = Esp32Client(base_url="http://192.168.1.50", client=http_client)
        result = await esp32.pulse_relay(duration_ms=500)
        assert result["accepted"] is True
        assert result["duration_ms"] == 500


@pytest.mark.asyncio
async def test_timeout_results_in_device_unavailable_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout")

    async with _make_client(handler) as http_client:
        esp32 = Esp32Client(base_url="http://192.168.1.50", client=http_client)
        with pytest.raises(DeviceUnavailableError):
            await esp32.status()


@pytest.mark.asyncio
async def test_non_json_response_maps_to_device_protocol_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=200, content="not-json")

    async with _make_client(handler) as http_client:
        esp32 = Esp32Client(base_url="http://192.168.1.50", client=http_client)
        with pytest.raises(DeviceProtocolError):
            await esp32.health()


@pytest.mark.asyncio
async def test_http_500_maps_to_device_protocol_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=500, json={"error": "boom"})

    async with _make_client(handler) as http_client:
        esp32 = Esp32Client(base_url="http://192.168.1.50", client=http_client)
        with pytest.raises(DeviceProtocolError):
            await esp32.status()


@pytest.mark.asyncio
async def test_connection_error_maps_to_device_unavailable_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed", request=request)

    async with _make_client(handler) as http_client:
        esp32 = Esp32Client(base_url="http://192.168.1.50", client=http_client)
        with pytest.raises(DeviceUnavailableError):
            await esp32.pulse_relay(duration_ms=500)
