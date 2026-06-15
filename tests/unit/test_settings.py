import pytest
from pydantic import ValidationError

from frostfire.config.settings import Settings


def test_valid_settings_from_defaults() -> None:
    settings = Settings(_env_file=None)
    assert settings.APP_HOST == "0.0.0.0"
    assert settings.APP_PORT == 8080
    assert settings.POWER_PRESS_DURATION_MS == 500


def test_missing_or_invalid_api_token_rejected() -> None:
    with pytest.raises(ValidationError) as exc:
        Settings(API_TOKEN="short", _env_file=None)
    assert exc.value.errors()[0]["type"] == "string_too_short"
