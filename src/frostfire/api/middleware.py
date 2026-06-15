"""API middleware utilities."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from time import perf_counter
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp
from structlog import get_logger

from frostfire.infrastructure.metrics import Metrics


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach request IDs and log basic request metrics."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id
        app_metrics = getattr(request.app.state, "metrics", None)
        if isinstance(app_metrics, Metrics):
            app_metrics.record_request()

        start = perf_counter()
        response = await call_next(request)
        duration_ms = (perf_counter() - start) * 1000

        response.headers["X-Request-ID"] = request_id

        logger = get_logger()
        logger.info(
            "request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
            remote_addr=(request.client.host if request.client else None),
        )
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests with excessive payload sizes."""

    def __init__(self, app: ASGIApp, *, max_body_size: int) -> None:
        super().__init__(app)
        self._max_body_size = max_body_size

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                size = int(content_length)
            except ValueError:
                logger = get_logger()
                logger.warning(
                    "request_size_limit_invalid_content_length",
                    content_length=content_length,
                    request_id=getattr(request.state, "request_id", None),
                )
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": {
                            "code": "bad_request",
                            "message": "invalid content-length header",
                            "details": {"content_length": content_length},
                        }
                    },
                )

            if size > self._max_body_size:
                logger = get_logger()
                logger.warning(
                    "request_size_limit_exceeded",
                    content_length=size,
                    request_id=getattr(request.state, "request_id", None),
                )
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": {
                            "code": "bad_request",
                            "message": "request body exceeds size limit",
                            "details": {
                                "max_bytes": self._max_body_size,
                                "content_length": size,
                            },
                        }
                    },
                )

        return await call_next(request)
