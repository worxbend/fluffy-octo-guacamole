"""Device-oriented application services."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from frostfire.domain.errors import DeviceProtocolError, DeviceUnavailableError, FrostfireError
from frostfire.domain.models import DeviceStatus
from frostfire.infrastructure.esp32_client import Esp32Client
from frostfire.infrastructure.metrics import Metrics


class DeviceService:
    def __init__(
        self,
        *,
        esp32_client: Esp32Client,
        device_name: str,
        esp32_base_url: str,
        metrics: Metrics | None = None,
    ) -> None:
        self._esp32_client = esp32_client
        self._device_name = device_name
        self._ip_address = self._extract_ip(esp32_base_url)
        self._metrics = metrics

    async def check_readiness(self) -> dict[str, Any]:
        try:
            await self._esp32_client.health()
        except FrostfireError as exc:
            if self._metrics is not None:
                self._metrics.set_esp32_online(False)
            return {
                "ready": False,
                "esp32": {
                    "online": False,
                    "error": str(exc),
                },
            }
        if self._metrics is not None:
            self._metrics.set_esp32_online(True)
        return {"ready": True, "esp32": {"online": True}}

    async def get_status(self) -> DeviceStatus:
        try:
            status = await self._esp32_client.status()
        except (DeviceUnavailableError, DeviceProtocolError):
            return DeviceStatus(
                online=False,
                device_name=self._device_name,
                ip_address=self._ip_address,
                firmware_version=None,
                relay_state=None,
                uptime_seconds=None,
                rssi=None,
            )

        return DeviceStatus(
            online=True,
            device_name=status.get("device", self._device_name),
            ip_address=self._ip_address,
            firmware_version=status.get("firmware_version"),
            relay_state=status.get("relay_state"),
            uptime_seconds=status.get("uptime_seconds"),
            rssi=status.get("rssi"),
        )

    @staticmethod
    def _extract_ip(base_url: str) -> str | None:
        parsed = urlparse(base_url)
        return parsed.hostname
