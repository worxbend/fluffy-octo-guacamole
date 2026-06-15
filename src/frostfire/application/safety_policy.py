"""Policy guards that enforce safe power command execution."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from time import monotonic

from frostfire.domain.enums import PowerAction
from frostfire.domain.errors import CommandInProgressError, CommandRejectedError, UnsafeCommandError


class SafetyPolicy:
    """Enforce safe execution semantics for power commands."""

    def __init__(
        self,
        *,
        min_command_interval_seconds: float,
        command_lock_timeout_seconds: float,
        now: Callable[[], float] | None = None,
    ) -> None:
        self._min_command_interval_seconds = min_command_interval_seconds
        self._command_lock_timeout_seconds = command_lock_timeout_seconds
        self._lock = asyncio.Lock()
        self._now = now or monotonic
        self._last_successful_command_at: float | None = None

    def validate_power_action(
        self,
        *,
        action: PowerAction,
        duration_ms: int,
        confirm: bool = False,
    ) -> None:
        if action == PowerAction.PRESS:
            if not 300 <= duration_ms <= 1000:
                raise UnsafeCommandError(
                    f"press duration must be between 300 and 1000 ms, got {duration_ms}"
                )
        elif action == PowerAction.FORCE_OFF:
            if not 3000 <= duration_ms <= 10000:
                raise UnsafeCommandError(
                    f"force-off duration must be between 3000 and 10000 ms, got {duration_ms}"
                )
            if not confirm:
                raise UnsafeCommandError("force-off requires confirm=true")
        else:
            raise CommandRejectedError(f"unsupported action: {action}")

    def mark_last_successful_command(self) -> None:
        self._last_successful_command_at = self._now()

    @asynccontextmanager
    async def command_lock(self) -> AsyncIterator[None]:
        try:
            await asyncio.wait_for(self._lock.acquire(), timeout=self._command_lock_timeout_seconds)
        except TimeoutError as exc:
            raise CommandInProgressError("another command is already in progress") from exc

        try:
            self._validate_interval_since_last_command()
            yield
        finally:
            self._lock.release()

    def _validate_interval_since_last_command(self) -> None:
        last = self._last_successful_command_at
        if last is None:
            return

        elapsed = self._now() - last
        if elapsed < self._min_command_interval_seconds:
            raise CommandRejectedError(
                f"minimum command interval is {self._min_command_interval_seconds}s"
            )
