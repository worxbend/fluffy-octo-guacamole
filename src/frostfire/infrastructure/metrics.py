"""Simple in-memory runtime metrics."""

from __future__ import annotations


class Metrics:
    """Minimal metrics container used for observability endpoints."""

    def __init__(self) -> None:
        self.requests_total = 0
        self.power_commands_total = 0
        self.power_command_failures_total = 0
        self.esp32_request_duration_seconds = 0.0
        self._esp32_request_duration_count = 0
        self._esp32_request_duration_sum = 0.0
        self.esp32_online = 0

    def record_request(self) -> None:
        self.requests_total += 1

    def record_power_command_total(self) -> None:
        self.power_commands_total += 1

    def record_power_command_failure(self) -> None:
        self.power_command_failures_total += 1

    def record_esp32_request_duration(self, duration_seconds: float) -> None:
        self.esp32_request_duration_seconds = duration_seconds
        self._esp32_request_duration_count += 1
        self._esp32_request_duration_sum += duration_seconds

    def set_esp32_online(self, online: bool) -> None:
        self.esp32_online = 1 if online else 0

    @property
    def esp32_request_duration_seconds_count(self) -> int:
        return self._esp32_request_duration_count

    @property
    def esp32_request_duration_seconds_sum(self) -> float:
        return self._esp32_request_duration_sum

    def render_prometheus(self) -> str:
        return (
            "# HELP frostfire_requests_total Total number of HTTP requests handled.\n"
            "# TYPE frostfire_requests_total counter\n"
            f"frostfire_requests_total {self.requests_total}\n"
            "# HELP frostfire_power_commands_total Total power command attempts executed.\n"
            "# TYPE frostfire_power_commands_total counter\n"
            f"frostfire_power_commands_total {self.power_commands_total}\n"
            "# HELP frostfire_power_command_failures_total Total failed power command attempts.\n"
            "# TYPE frostfire_power_command_failures_total counter\n"
            f"frostfire_power_command_failures_total {self.power_command_failures_total}\n"
            "# HELP frostfire_esp32_request_duration_seconds "
            "Seconds spent in ESP32 client requests.\n"
            "# TYPE frostfire_esp32_request_duration_seconds gauge\n"
            f"frostfire_esp32_request_duration_seconds {self.esp32_request_duration_seconds}\n"
            "# HELP frostfire_esp32_request_duration_seconds_count "
            "Total ESP32 request count.\n"
            "# TYPE frostfire_esp32_request_duration_seconds_count counter\n"
            "frostfire_esp32_request_duration_seconds_count "
            f"{self.esp32_request_duration_seconds_count}\n"
            "# HELP frostfire_esp32_request_duration_seconds_sum "
            "Total duration of ESP32 requests in seconds.\n"
            "# TYPE frostfire_esp32_request_duration_seconds_sum counter\n"
            "frostfire_esp32_request_duration_seconds_sum "
            f"{self.esp32_request_duration_seconds_sum}\n"
            "# HELP frostfire_esp32_online "
            "Whether the most recent ESP32 health check succeeded.\n"
            "# TYPE frostfire_esp32_online gauge\n"
            f"frostfire_esp32_online {self.esp32_online}\n"
        )
