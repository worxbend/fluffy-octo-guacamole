"""Pydantic schemas used by API responses."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from frostfire.domain.models import PowerCommandResult


class HealthResponse(BaseModel):
    status: Literal["ok"] = Field(default="ok")
    service: str
    version: str


class ReadyEsp32Status(BaseModel):
    online: bool
    error: str | None = None


class ReadyResponse(BaseModel):
    ready: bool
    esp32: ReadyEsp32Status


class DeviceStatusResponse(BaseModel):
    online: bool
    device_name: str | None
    ip_address: str | None
    firmware_version: str | None
    relay_state: str | None
    uptime_seconds: int | None
    rssi: int | None


class ForceOffRequest(BaseModel):
    confirm: bool = False


class PowerCommandResponse(PowerCommandResult):
    pass
