"""Application settings loaded from environment variables."""

from __future__ import annotations

from typing import Final

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_SECURE_API_TOKEN_MIN_LENGTH: Final = 8


class Settings(BaseSettings):
    APP_HOST: str = Field(default="0.0.0.0")
    APP_PORT: int = Field(default=8080, ge=1, le=65535)

    API_TOKEN: str = Field(default="", min_length=_SECURE_API_TOKEN_MIN_LENGTH)

    ESP32_BASE_URL: str = Field(default="http://192.168.1.50")
    ESP32_TIMEOUT_SECONDS: float = Field(default=3.0, gt=0)

    POWER_PRESS_DURATION_MS: int = Field(default=500, ge=300, le=1000)
    FORCE_OFF_PRESS_DURATION_MS: int = Field(default=5000, ge=3000, le=10000)

    MIN_COMMAND_INTERVAL_SECONDS: float = Field(default=2.0, ge=0)
    COMMAND_LOCK_TIMEOUT_SECONDS: float = Field(default=10.0, ge=0)
    IDEMPOTENCY_TTL_SECONDS: float = Field(default=0.0, ge=0)

    LOG_LEVEL: str = Field(default="INFO")

    CORS_ENABLED: bool = Field(default=False)
    CORS_ALLOWED_ORIGINS: str = Field(default="")
    ENABLE_AUDIT_LOG: bool = Field(default=True)
    ENABLE_OPENAPI_DOCS: bool = Field(default=False)
    DEVICE_NAME: str = Field(default="frostfire-esp32-main-pc")
    MAX_REQUEST_BODY_BYTES: int = Field(default=10_240, gt=0, le=1_048_576)

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    @field_validator("APP_HOST")
    @classmethod
    def _validate_host(cls, value: str) -> str:
        if not value:
            raise ValueError("APP_HOST cannot be empty")
        return value

    @field_validator("ESP32_BASE_URL")
    @classmethod
    def _validate_esp32_base_url(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("ESP32_BASE_URL must include http:// or https://")
        return value.rstrip("/")

    @field_validator("LOG_LEVEL")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        normalized = value.upper()
        allowed = {
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
            "CRITICAL",
            "NOTSET",
        }
        if normalized not in allowed:
            raise ValueError(
                "LOG_LEVEL must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL, NOTSET"
            )
        return normalized

    @field_validator("API_TOKEN")
    @classmethod
    def _validate_api_token(cls, value: str) -> str:
        if value.strip() == "":
            raise ValueError("API_TOKEN must not be blank")
        if len(value) < _SECURE_API_TOKEN_MIN_LENGTH:
            raise ValueError("API_TOKEN must be at least 8 characters long")
        return value


def load_settings() -> Settings:
    return Settings()
