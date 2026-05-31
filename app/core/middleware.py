"""Custom middleware: request id and a lightweight rate-limit scaffold."""

import time
import uuid
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.core.logging import get_logger

logger = get_logger("request")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request id and store the client IP for audit logging."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        client = request.client
        request.state.client_ip = client.host if client else None
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class SimpleRateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory fixed-window rate limiter.

    This is a minimal architecture placeholder. For production behind multiple
    workers/instances, back it with Redis. Disabled by default unless ``enabled``.
    """

    def __init__(self, app, *, max_requests: int = 100, window_seconds: int = 60, enabled: bool = False):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.enabled = enabled
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)

        client = request.client
        key = client.host if client else "anonymous"
        now = time.monotonic()
        window = self._hits[key]
        while window and window[0] <= now - self.window_seconds:
            window.popleft()
        if len(window) >= self.max_requests:
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": {"code": "rate_limited", "message": "Too many requests"},
                },
            )
        window.append(now)
        return await call_next(request)


def register_middleware(app: FastAPI) -> None:
    app.add_middleware(RequestContextMiddleware)
    # Rate limiter registered but disabled by default; flip enabled=True to use.
    app.add_middleware(SimpleRateLimitMiddleware, enabled=False)
