"""FastAPI application factory for Frostfire."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from frostfire import __version__
from frostfire.api.routes import create_health_router
from frostfire.config import settings as settings_module
from frostfire.infrastructure.logging import configure_logging


def create_app() -> FastAPI:
    app_settings = settings_module.load_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        configure_logging(app_settings)
        yield

    app = FastAPI(
        title="Frostfire Backend",
        version=__version__,
        docs_url="/docs" if app_settings.ENABLE_OPENAPI_DOCS else None,
        redoc_url="/redoc" if app_settings.ENABLE_OPENAPI_DOCS else None,
        openapi_url="/openapi.json" if app_settings.ENABLE_OPENAPI_DOCS else None,
        lifespan=lifespan,
    )

    app.include_router(create_health_router(service="frostfire-backend", version="0.1.0"))
    return app
