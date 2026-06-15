from __future__ import annotations

import re

from fastapi.testclient import TestClient

from frostfire.app import create_app
from frostfire.config.settings import Settings


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        API_TOKEN="test-token",
    )


def _extract_metric_value(body: str, metric_name: str) -> float:
    pattern = rf"^{re.escape(metric_name)} (\d+(?:\.\d+)?)$"
    match = re.search(pattern, body, re.MULTILINE)
    assert match is not None, f"missing metric: {metric_name}"
    return float(match.group(1))


def test_metrics_endpoint_returns_prometheus_payload() -> None:
    app = create_app(_settings())

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/health").status_code == 200
        metrics_response = client.get("/metrics")

    assert metrics_response.status_code == 200
    body = metrics_response.text

    assert _extract_metric_value(body, "frostfire_requests_total") >= 3
    assert _extract_metric_value(body, "frostfire_power_commands_total") == 0
    assert _extract_metric_value(body, "frostfire_power_command_failures_total") == 0
    assert _extract_metric_value(body, "frostfire_esp32_online") in {0.0, 1.0}
