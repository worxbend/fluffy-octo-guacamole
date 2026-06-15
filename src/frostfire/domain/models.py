"""Core domain models for Frostfire."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from frostfire.domain.enums import PowerAction


class DeviceStatus(BaseModel):
    online: bool
    device_name: str | None
    ip_address: str | None
    firmware_version: str | None
    relay_state: str | None
    uptime_seconds: int | None
    rssi: int | None


class PowerCommandResult(BaseModel):
    action: PowerAction
    accepted: bool
    executed: bool
    duration_ms: int
    device_response: dict[str, Any] | None
    message: str
