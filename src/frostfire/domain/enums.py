"""Domain enumerations for Frostfire operations."""

from __future__ import annotations

from enum import StrEnum


class PowerAction(StrEnum):
    PRESS = "press"
    FORCE_OFF = "force_off"
    RESET = "reset"
