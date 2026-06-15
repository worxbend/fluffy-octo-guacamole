from __future__ import annotations

import asyncio

import pytest

from frostfire.application.power_service import PowerService
from frostfire.application.safety_policy import SafetyPolicy
from frostfire.domain.enums import PowerAction
from frostfire.domain.errors import CommandInProgressError, ConfirmationRequiredError


class FakeEsp32Client:
    def __init__(self) -> None:
        self.calls: list[int] = []
        self.started = asyncio.Event()
        self.allow = asyncio.Event()

    async def pulse_relay(self, duration_ms: int) -> dict[str, object]:
        self.calls.append(duration_ms)
        self.started.set()
        await self.allow.wait()
        return {
            "accepted": True,
            "duration_ms": duration_ms,
            "message": "relay pulsed",
        }

    async def close(self) -> None:  # pragma: no cover - interface compatibility
        return None


@pytest.mark.asyncio
async def test_power_press_uses_configured_duration() -> None:
    esp32 = FakeEsp32Client()
    policy = SafetyPolicy(min_command_interval_seconds=0.0, command_lock_timeout_seconds=1.0)
    service = PowerService(
        esp32_client=esp32,
        safety_policy=policy,
        power_press_duration_ms=500,
        force_off_press_duration_ms=5000,
    )
    esp32.allow.set()

    result = await service.execute_power_action(PowerAction.PRESS)
    assert result.accepted is True
    assert result.duration_ms == 500
    assert result.action == PowerAction.PRESS
    assert esp32.calls == [500]


@pytest.mark.asyncio
async def test_force_off_requires_confirmation() -> None:
    esp32 = FakeEsp32Client()
    policy = SafetyPolicy(min_command_interval_seconds=0.0, command_lock_timeout_seconds=1.0)
    service = PowerService(
        esp32_client=esp32,
        safety_policy=policy,
        power_press_duration_ms=500,
        force_off_press_duration_ms=5000,
    )
    esp32.allow.set()

    with pytest.raises(ConfirmationRequiredError):
        await service.execute_power_action(PowerAction.FORCE_OFF, confirm=False)


@pytest.mark.asyncio
async def test_concurrent_commands_fail_fast() -> None:
    esp32 = FakeEsp32Client()
    policy = SafetyPolicy(min_command_interval_seconds=0.0, command_lock_timeout_seconds=0.05)
    service = PowerService(
        esp32_client=esp32,
        safety_policy=policy,
        power_press_duration_ms=500,
        force_off_press_duration_ms=5000,
    )

    task_a = asyncio.create_task(service.execute_power_action(PowerAction.PRESS))
    await esp32.started.wait()
    task_b = asyncio.create_task(service.execute_power_action(PowerAction.PRESS))

    with pytest.raises(CommandInProgressError):
        await task_b

    esp32.allow.set()
    result = await task_a
    assert result.action == PowerAction.PRESS
