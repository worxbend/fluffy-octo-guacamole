"""API dependency helpers."""

from __future__ import annotations

import hmac
from typing import Annotated, cast

from fastapi import Depends, Header, HTTPException, Request, status

from frostfire.application.device_service import DeviceService
from frostfire.application.power_service import PowerService
from frostfire.config.settings import Settings


def get_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_power_service(request: Request) -> PowerService:
    return cast(PowerService, request.app.state.power_service)


def get_device_service(request: Request) -> DeviceService:
    return cast(DeviceService, request.app.state.device_service)


async def require_api_token(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing token")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid token")

    incoming_token = authorization.split(" ", 1)[1]
    if not hmac.compare_digest(incoming_token, settings.API_TOKEN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid token")
