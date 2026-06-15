"""HTTP client for communicating with the ESP32 device."""

from __future__ import annotations

from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from frostfire.domain.errors import DeviceProtocolError, DeviceUnavailableError


class Esp32HealthResponse(BaseModel):
    status: str
    device: str
    firmware_version: str


class Esp32StatusResponse(BaseModel):
    device: str
    firmware_version: str
    relay_state: str
    uptime_seconds: int
    rssi: int


class Esp32PulseResponse(BaseModel):
    accepted: bool
    duration_ms: int
    message: str


ModelT = TypeVar("ModelT", bound=BaseModel)


class Esp32Client:
    """Simple wrapper over ESP32 relay API."""

    def __init__(self, base_url: str, client: httpx.AsyncClient) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = client

    async def health(self) -> dict[str, Any]:
        return await self._request("/health", Esp32HealthResponse)

    async def status(self) -> dict[str, Any]:
        return await self._request("/status", Esp32StatusResponse)

    async def pulse_relay(self, duration_ms: int) -> dict[str, Any]:
        payload = {"duration_ms": duration_ms}
        return await self._request(
            "/relay/pulse",
            Esp32PulseResponse,
            method="POST",
            json=payload,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _request(
        self,
        path: str,
        parser: type[ModelT],
        method: str = "GET",
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            response = await self._client.request(
                method=method,
                url=f"{self._base_url}{path}",
                json=json,
            )
        except httpx.TimeoutException as exc:
            raise DeviceUnavailableError("ESP32 device timed out") from exc
        except (httpx.ConnectError, httpx.RequestError) as exc:
            raise DeviceUnavailableError("ESP32 device is unavailable") from exc

        if response.status_code >= 400:
            raise DeviceProtocolError(f"ESP32 protocol error with status={response.status_code}")

        try:
            payload = response.json()
        except ValueError as exc:
            raise DeviceProtocolError("ESP32 returned invalid JSON") from exc

        try:
            return parser.model_validate(payload).model_dump()
        except ValidationError as exc:
            raise DeviceProtocolError("ESP32 returned unexpected response schema") from exc
