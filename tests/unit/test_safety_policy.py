from __future__ import annotations

import asyncio

import pytest

from frostfire.application.safety_policy import SafetyPolicy
from frostfire.domain.enums import PowerAction
from frostfire.domain.errors import CommandInProgressError, CommandRejectedError, UnsafeCommandError


def test_allows_first_command() -> None:
    policy = SafetyPolicy(
        min_command_interval_seconds=2.0,
        command_lock_timeout_seconds=1.0,
    )
    policy.validate_power_action(action=PowerAction.PRESS, duration_ms=500)
    policy.validate_power_action(
        action=PowerAction.FORCE_OFF,
        duration_ms=5000,
        confirm=True,
    )


@pytest.mark.asyncio
async def test_rejects_rapid_commands() -> None:
    now = 1_000.0

    def clock() -> float:
        nonlocal now
        return now

    policy = SafetyPolicy(
        min_command_interval_seconds=10.0,
        command_lock_timeout_seconds=1.0,
        now=clock,
    )
    policy.mark_last_successful_command()
    with pytest.raises(CommandRejectedError):
        async with policy.command_lock():
            pass

    now += 10.1
    async with policy.command_lock():
        pass


def test_rejects_unsafe_durations() -> None:
    policy = SafetyPolicy(
        min_command_interval_seconds=2.0,
        command_lock_timeout_seconds=1.0,
    )
    with pytest.raises(UnsafeCommandError):
        policy.validate_power_action(action=PowerAction.PRESS, duration_ms=200)
    with pytest.raises(UnsafeCommandError):
        policy.validate_power_action(action=PowerAction.FORCE_OFF, duration_ms=12000)


def test_requires_confirmation_for_force_off() -> None:
    policy = SafetyPolicy(
        min_command_interval_seconds=2.0,
        command_lock_timeout_seconds=1.0,
    )
    with pytest.raises(UnsafeCommandError):
        policy.validate_power_action(action=PowerAction.FORCE_OFF, duration_ms=5000, confirm=False)


@pytest.mark.asyncio
async def test_prevents_concurrent_commands() -> None:
    policy = SafetyPolicy(
        min_command_interval_seconds=0.0,
        command_lock_timeout_seconds=0.05,
    )
    started = asyncio.Event()

    async def run_first() -> None:
        async with policy.command_lock():
            started.set()
            await asyncio.sleep(0.2)

    task = asyncio.create_task(run_first())
    await started.wait()
    with pytest.raises(CommandInProgressError):
        async with policy.command_lock():
            pass
    await task
