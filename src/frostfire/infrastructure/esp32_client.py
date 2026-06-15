"""HTTP client for communicating with the ESP32 device."""

from __future__ import annotations

from time import perf_counter
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from frostfire.domain.errors import DeviceProtocolError, DeviceUnavailableError
from frostfire.infrastructure.metrics import Metrics


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

    def __init__(
        self, base_url: str, client: httpx.AsyncClient, metrics: Metrics | None = None
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = client
        self._metrics = metrics

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
        start = perf_counter()
        try:
            response = await self._client.request(
                method=method,
                url=f"{self._base_url}{path}",
                json=json,
            )
        except httpx.TimeoutException as exc:
            self._record_esp32_request_duration(start)
            raise DeviceUnavailableError("ESP32 device timed out") from exc
        except (httpx.ConnectError, httpx.RequestError) as exc:
            self._record_esp32_request_duration(start)
            raise DeviceUnavailableError("ESP32 device is unavailable") from exc

        if response.status_code >= 400:
            self._record_esp32_request_duration(start)
            raise DeviceProtocolError(f"ESP32 protocol error with status={response.status_code}")

        try:
            payload = response.json()
        except ValueError as exc:
            self._record_esp32_request_duration(start)
            raise DeviceProtocolError("ESP32 returned invalid JSON") from exc

        try:
            parsed_payload = parser.model_validate(payload).model_dump()
            self._record_esp32_request_duration(start)
            return parsed_payload
        except ValidationError as exc:
            self._record_esp32_request_duration(start)
            raise DeviceProtocolError("ESP32 returned unexpected response schema") from exc

    def _record_esp32_request_duration(self, start: float) -> None:
        if self._metrics is not None:
            duration = perf_counter() - start
            self._metrics.record_esp32_request_duration(duration)
