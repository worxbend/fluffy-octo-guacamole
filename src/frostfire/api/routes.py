"""API route declarations."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.responses import PlainTextResponse

from frostfire.api.dependencies import (
    get_device_service,
    get_power_service,
    require_api_token,
)
from frostfire.api.schemas import (
    DeviceStatusResponse,
    ForceOffRequest,
    HealthResponse,
    PowerCommandResponse,
    ReadyResponse,
)
from frostfire.application.device_service import DeviceService
from frostfire.application.power_service import PowerService
from frostfire.domain.enums import PowerAction
from frostfire.infrastructure.metrics import Metrics


def create_health_router(*, service: str, version: str) -> APIRouter:
    router = APIRouter()

    @router.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(service=service, version=version)

    return router


def create_readiness_router() -> APIRouter:
    router = APIRouter()

    @router.get("/ready", response_model=ReadyResponse)
    async def ready(
        device_service: Annotated[DeviceService, Depends(get_device_service)],
    ) -> ReadyResponse:
        return ReadyResponse.model_validate(await device_service.check_readiness())

    return router


def create_device_router() -> APIRouter:
    router = APIRouter()

    @router.get("/device/status", response_model=DeviceStatusResponse)
    async def status(
        device_service: Annotated[DeviceService, Depends(get_device_service)],
    ) -> DeviceStatusResponse:
        return DeviceStatusResponse.model_validate(await device_service.get_status())

    return router


def create_power_router() -> APIRouter:
    router = APIRouter(dependencies=[Depends(require_api_token)])

    @router.post(
        "/power/press",
        response_model=PowerCommandResponse,
        status_code=status.HTTP_200_OK,
    )
    async def press(
        request: Request,
        power_service: Annotated[PowerService, Depends(get_power_service)],
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    ) -> PowerCommandResponse:
        result = await power_service.execute_power_action(
            PowerAction.PRESS,
            idempotency_key=idempotency_key,
            request_id=getattr(request.state, "request_id", None),
        )
        return PowerCommandResponse.model_validate(result.model_dump())

    @router.post(
        "/power/force-off",
        response_model=PowerCommandResponse,
        status_code=status.HTTP_200_OK,
    )
    async def force_off(
        request: Request,
        payload: ForceOffRequest,
        power_service: Annotated[PowerService, Depends(get_power_service)],
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    ) -> PowerCommandResponse:
        result = await power_service.execute_power_action(
            PowerAction.FORCE_OFF,
            confirm=payload.confirm,
            idempotency_key=idempotency_key,
            request_id=getattr(request.state, "request_id", None),
        )
        return PowerCommandResponse.model_validate(result.model_dump())

    return router


def create_api_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    router.include_router(create_device_router())
    router.include_router(create_power_router())
    return router


def create_metrics_router() -> APIRouter:
    router = APIRouter()

    @router.get("/metrics", response_class=PlainTextResponse, include_in_schema=False)
    async def metrics(request: Request) -> str:
        app_metrics = getattr(request.app.state, "metrics", None)
        if not isinstance(app_metrics, Metrics):
            return "# no metrics collector configured\n"
        return app_metrics.render_prometheus()

    return router
