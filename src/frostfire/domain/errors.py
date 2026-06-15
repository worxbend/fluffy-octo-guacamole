"""Domain exceptions for Frostfire."""

from __future__ import annotations


class FrostfireError(Exception):
    """Base domain exception."""

    code: str = "internal_error"
    http_status: int = 500


class DeviceUnavailableError(FrostfireError):
    """Raised when the ESP32 device cannot be reached."""

    code = "device_unavailable"
    http_status = 503


class CommandRejectedError(FrostfireError):
    """Raised when a command violates policy."""

    code = "unsafe_command"
    http_status = 422


class CommandInProgressError(FrostfireError):
    """Raised when another command is already executing."""

    code = "command_in_progress"
    http_status = 409


class UnsafeCommandError(FrostfireError):
    """Raised when requested command is unsafe."""

    code = "unsafe_command"
    http_status = 422


class DeviceProtocolError(FrostfireError):
    """Raised when the ESP32 returns an unexpected response."""

    code = "device_protocol_error"
    http_status = 503
