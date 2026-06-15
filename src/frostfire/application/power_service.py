"""Use cases for power control commands."""

from __future__ import annotations

from structlog import get_logger

from frostfire.domain.enums import PowerAction
from frostfire.domain.errors import CommandRejectedError
from frostfire.domain.models import PowerCommandResult
from frostfire.infrastructure.esp32_client import Esp32Client

from .safety_policy import SafetyPolicy


class PowerService:
    def __init__(
        self,
        *,
        esp32_client: Esp32Client,
        safety_policy: SafetyPolicy,
        power_press_duration_ms: int,
        force_off_press_duration_ms: int,
    ) -> None:
        self._esp32_client = esp32_client
        self._safety_policy = safety_policy
        self._power_press_duration_ms = power_press_duration_ms
        self._force_off_press_duration_ms = force_off_press_duration_ms

    async def execute_power_action(
        self,
        action: PowerAction,
        *,
        confirm: bool = False,
        request_id: str | None = None,
    ) -> PowerCommandResult:
        duration_ms = self._duration_for_action(action)

        self._safety_policy.validate_power_action(
            action=action,
            duration_ms=duration_ms,
            confirm=confirm,
        )

        async with self._safety_policy.command_lock():
            raw_result = await self._esp32_client.pulse_relay(duration_ms=duration_ms)

        self._safety_policy.mark_last_successful_command()

        accepted = bool(raw_result.get("accepted", False))
        executed = accepted
        duration = int(raw_result.get("duration_ms", duration_ms))
        message = str(raw_result.get("message", f"{action.value} power action"))

        logger = get_logger()
        logger.info(
            "power_command",
            request_id=request_id,
            action=action.value,
            duration_ms=duration,
            result=raw_result,
        )

        return PowerCommandResult(
            action=action,
            accepted=accepted,
            executed=executed,
            duration_ms=duration,
            device_response=raw_result,
            message=message,
        )

    def _duration_for_action(self, action: PowerAction) -> int:
        if action == PowerAction.PRESS:
            return self._power_press_duration_ms
        if action == PowerAction.FORCE_OFF:
            return self._force_off_press_duration_ms
        raise CommandRejectedError(f"unsupported action: {action}")
