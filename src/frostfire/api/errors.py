"""Unified error response handling."""

from __future__ import annotations

import traceback
from typing import Any

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.requests import Request
from structlog import get_logger

from frostfire.domain.errors import FrostfireError

ErrorResponse = dict[str, dict[str, Any]]


def add_error_handlers(app: FastAPI) -> None:
    logger = get_logger()

    @app.exception_handler(FrostfireError)
    async def handle_frostfire_error(request: Request, exc: FrostfireError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.warning(
            "api_error",
            request_id=request_id,
            code=exc.code,
            message=str(exc),
            path=request.url.path,
        )
        payload: ErrorResponse = {
            "error": {
                "code": exc.code,
                "message": str(exc),
                "details": {},
            },
        }
        return JSONResponse(status_code=exc.http_status, content=payload)

    @app.exception_handler(RequestValidationError)
    @app.exception_handler(ValidationError)
    async def handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.warning(
            "api_error",
            request_id=request_id,
            code="bad_request",
            message=str(exc),
            path=request.url.path,
        )
        payload: ErrorResponse = {
            "error": {
                "code": "bad_request",
                "message": "invalid request payload",
                "details": {"details": str(exc)},
            },
        }
        return JSONResponse(status_code=400, content=payload)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.error(
            "api_error_unhandled",
            request_id=request_id,
            code="internal_error",
            message=str(exc),
            path=request.url.path,
        )
        logger.debug(traceback.format_exc())
        payload: ErrorResponse = {
            "error": {
                "code": "internal_error",
                "message": "unexpected internal error",
                "details": {},
            },
        }
        return JSONResponse(status_code=500, content=payload)
