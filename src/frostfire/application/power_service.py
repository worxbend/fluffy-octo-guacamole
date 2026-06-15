"""Use cases for power control commands."""

from __future__ import annotations

from time import monotonic

from structlog import get_logger

from frostfire.domain.enums import PowerAction
from frostfire.domain.errors import CommandRejectedError
from frostfire.domain.models import PowerCommandResult
from frostfire.infrastructure.esp32_client import Esp32Client
from frostfire.infrastructure.metrics import Metrics

from .safety_policy import SafetyPolicy


class PowerService:
    _CACHE_PREFIX = "frostfire:power:"

    def __init__(
        self,
        *,
        esp32_client: Esp32Client,
        safety_policy: SafetyPolicy,
        power_press_duration_ms: int,
        force_off_press_duration_ms: int,
        metrics: Metrics | None = None,
        idempotency_ttl_seconds: float = 0.0,
    ) -> None:
        self._esp32_client = esp32_client
        self._safety_policy = safety_policy
        self._power_press_duration_ms = power_press_duration_ms
        self._force_off_press_duration_ms = force_off_press_duration_ms
        self._metrics = metrics
        self._idempotency_ttl_seconds = idempotency_ttl_seconds
        self._idempotency_cache: dict[str, tuple[float, PowerCommandResult]] = {}
        self._now = monotonic

    async def execute_power_action(
        self,
        action: PowerAction,
        *,
        confirm: bool = False,
        idempotency_key: str | None = None,
        request_id: str | None = None,
    ) -> PowerCommandResult:
        cached_result = self._consume_cached_result(idempotency_key)
        if cached_result is not None:
            return cached_result

        duration_ms = self._duration_for_action(action)

        self._safety_policy.validate_power_action(
            action=action,
            duration_ms=duration_ms,
            confirm=confirm,
        )

        try:
            async with self._safety_policy.command_lock():
                raw_result = await self._esp32_client.pulse_relay(duration_ms=duration_ms)
        except Exception:
            if self._metrics is not None:
                self._metrics.record_power_command_failure()
            raise

        self._safety_policy.mark_last_successful_command()
        if self._metrics is not None:
            self._metrics.record_power_command_total()

        accepted = bool(raw_result.get("accepted", False))
        executed = accepted
        duration = int(raw_result.get("duration_ms", duration_ms))
        message = str(raw_result.get("message", f"{action.value} power action"))

        result = PowerCommandResult(
            action=action,
            accepted=accepted,
            executed=executed,
            duration_ms=duration,
            device_response=raw_result,
            message=message,
        )

        if idempotency_key:
            self._store_idempotent_result(idempotency_key, result)

        logger = get_logger()
        logger.info(
            "power_command",
            request_id=request_id,
            action=action.value,
            duration_ms=duration,
            result=raw_result,
            esp32_status="online",
        )

        return result

    def _consume_cached_result(
        self,
        idempotency_key: str | None,
    ) -> PowerCommandResult | None:
        if not idempotency_key or self._idempotency_ttl_seconds <= 0:
            return None

        self._cleanup_expired_entries()
        cached = self._idempotency_cache.get(self._build_cache_key(idempotency_key))
        if cached is None:
            return None

        expires_at, result = cached
        if self._now() >= expires_at:
            del self._idempotency_cache[self._build_cache_key(idempotency_key)]
            return None

        return result.model_copy(deep=True)

    def _store_idempotent_result(
        self,
        idempotency_key: str,
        result: PowerCommandResult,
    ) -> None:
        if self._idempotency_ttl_seconds <= 0:
            return
        self._cleanup_expired_entries()
        self._idempotency_cache[self._build_cache_key(idempotency_key)] = (
            self._now() + self._idempotency_ttl_seconds,
            result.model_copy(deep=True),
        )

    def _cleanup_expired_entries(self) -> None:
        now = self._now()
        expired = [
            key
            for key, (expires_at, _result) in self._idempotency_cache.items()
            if expires_at <= now
        ]
        for key in expired:
            del self._idempotency_cache[key]

    @staticmethod
    def _build_cache_key(idempotency_key: str) -> str:
        return f"{PowerService._CACHE_PREFIX}{idempotency_key}"

    def _duration_for_action(self, action: PowerAction) -> int:
        if action == PowerAction.PRESS:
            return self._power_press_duration_ms
        if action == PowerAction.FORCE_OFF:
            return self._force_off_press_duration_ms
        raise CommandRejectedError(f"unsupported action: {action}")
