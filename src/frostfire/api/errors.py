"""Unified error response handling."""

from __future__ import annotations

import traceback
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.requests import Request
from structlog import get_logger

from frostfire.domain.errors import FrostfireError

ErrorResponse = dict[str, dict[str, Any]]


def add_error_handlers(app: FastAPI) -> None:
    logger = get_logger()

    def _build_error_payload(
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> ErrorResponse:
        return {
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            }
        }

    def _http_exception_code(status_code: int) -> str:
        return {
            400: "bad_request",
            401: "unauthorized",
            403: "forbidden",
            404: "not_found",
            409: "command_in_progress",
            422: "unsafe_command",
            503: "device_unavailable",
        }.get(status_code, "internal_error")

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
        payload = _build_error_payload(code=exc.code, message=str(exc))
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
        payload = _build_error_payload(
            code="bad_request",
            message="invalid request payload",
            details={"details": str(exc)},
        )
        return JSONResponse(status_code=400, content=payload)

    @app.exception_handler(HTTPException)
    async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        code = _http_exception_code(exc.status_code)
        logger.warning(
            "api_error",
            request_id=request_id,
            code=code,
            message=str(exc.detail),
            path=request.url.path,
        )
        payload = _build_error_payload(
            code=code,
            message=str(exc.detail),
            details={"status_code": exc.status_code},
        )
        return JSONResponse(status_code=exc.status_code, content=payload)

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
        payload = _build_error_payload(
            code="internal_error",
            message="unexpected internal error",
        )
        return JSONResponse(status_code=500, content=payload)
