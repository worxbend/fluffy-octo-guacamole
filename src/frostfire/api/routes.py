"""API route declarations."""

from __future__ import annotations

from fastapi import APIRouter

from frostfire.api.schemas import HealthResponse


def create_health_router(*, service: str, version: str) -> APIRouter:
    router = APIRouter()

    @router.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(service=service, version=version)

    return router
