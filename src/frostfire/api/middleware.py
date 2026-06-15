"""API middleware utilities."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from time import perf_counter
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from structlog import get_logger


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach request IDs and log basic request metrics."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id

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
