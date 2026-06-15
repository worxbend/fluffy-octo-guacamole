"""FastAPI application factory for Frostfire."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from frostfire import __version__
from frostfire.api.errors import add_error_handlers
from frostfire.api.middleware import RequestIDMiddleware
from frostfire.api.routes import (
    create_api_router,
    create_health_router,
    create_metrics_router,
    create_readiness_router,
)
from frostfire.application.device_service import DeviceService
from frostfire.application.power_service import PowerService
from frostfire.application.safety_policy import SafetyPolicy
from frostfire.config.settings import Settings, load_settings
from frostfire.infrastructure.esp32_client import Esp32Client
from frostfire.infrastructure.logging import configure_logging
from frostfire.infrastructure.metrics import Metrics


def create_app(
    settings: Settings | None = None,
    *,
    power_service: PowerService | None = None,
    device_service: DeviceService | None = None,
) -> FastAPI:
    app_settings = settings or load_settings()

    configure_logging(app_settings)
    app_metrics = Metrics()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        managed_http_client: httpx.AsyncClient | None = None
        managed_esp32_client: Esp32Client | None = None
        managed_safety_policy: SafetyPolicy | None = None

        active_power_service = power_service
        active_device_service = device_service

        if active_power_service is None or active_device_service is None:
            managed_http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(app_settings.ESP32_TIMEOUT_SECONDS),
            )
            managed_esp32_client = Esp32Client(
                base_url=app_settings.ESP32_BASE_URL,
                client=managed_http_client,
                metrics=app_metrics,
            )
            managed_safety_policy = SafetyPolicy(
                min_command_interval_seconds=app_settings.MIN_COMMAND_INTERVAL_SECONDS,
                command_lock_timeout_seconds=app_settings.COMMAND_LOCK_TIMEOUT_SECONDS,
            )
            active_power_service = active_power_service or PowerService(
                esp32_client=managed_esp32_client,
                safety_policy=managed_safety_policy,
                power_press_duration_ms=app_settings.POWER_PRESS_DURATION_MS,
                force_off_press_duration_ms=app_settings.FORCE_OFF_PRESS_DURATION_MS,
                metrics=app_metrics,
                idempotency_ttl_seconds=app_settings.IDEMPOTENCY_TTL_SECONDS,
            )
            active_device_service = active_device_service or DeviceService(
                esp32_client=managed_esp32_client,
                device_name=app_settings.DEVICE_NAME,
                esp32_base_url=app_settings.ESP32_BASE_URL,
                metrics=app_metrics,
            )

        # make shared state available for handlers/dependencies
        app.state.settings = app_settings
        app.state.power_service = active_power_service
        app.state.device_service = active_device_service
        app.state.esp32_client = managed_esp32_client
        app.state.metrics = app_metrics
        app.state.safety_policy = managed_safety_policy

        yield

        if managed_http_client is not None:
            await managed_http_client.aclose()

    app = FastAPI(
        title="Frostfire Backend",
        version=__version__,
        docs_url="/docs" if app_settings.ENABLE_OPENAPI_DOCS else None,
        redoc_url="/redoc" if app_settings.ENABLE_OPENAPI_DOCS else None,
        openapi_url="/openapi.json" if app_settings.ENABLE_OPENAPI_DOCS else None,
        lifespan=lifespan,
    )

    add_error_handlers(app)
    app.add_middleware(RequestIDMiddleware)

    if app_settings.CORS_ENABLED:
        allowed_origins = [
            origin.strip()
            for origin in app_settings.CORS_ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins or ["*"],
            allow_methods=["*"],
            allow_headers=["*"],
            allow_credentials=False,
        )

    app.include_router(create_health_router(service="frostfire-backend", version=__version__))
    app.include_router(create_readiness_router())
    app.include_router(create_api_router())
    app.include_router(create_metrics_router())
    return app
