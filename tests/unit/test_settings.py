import pytest
from pydantic import ValidationError

from frostfire.config.settings import Settings


def test_valid_settings_from_defaults() -> None:
    settings = Settings(_env_file=None, API_TOKEN="change-me")
    assert settings.APP_HOST == "0.0.0.0"
    assert settings.APP_PORT == 8080
    assert settings.POWER_PRESS_DURATION_MS == 500


def test_missing_api_token_rejected() -> None:
    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None)
    assert exc.value.errors()[0]["type"] == "string_too_short"


def test_invalid_api_token_rejected() -> None:
    with pytest.raises(ValidationError) as exc:
        Settings(API_TOKEN="short", _env_file=None)
    assert exc.value.errors()[0]["type"] == "string_too_short"


def test_rejects_invalid_esp32_url() -> None:
    with pytest.raises(ValidationError) as exc:
        Settings(API_TOKEN="change-me", ESP32_BASE_URL="not-a-url", _env_file=None)
    assert exc.value.errors()[0]["type"] == "value_error"


def test_rejects_invalid_durations() -> None:
    with pytest.raises(ValidationError):
        Settings(
            API_TOKEN="change-me",
            POWER_PRESS_DURATION_MS=100,
            FORCE_OFF_PRESS_DURATION_MS=2000,
            _env_file=None,
        )
