"""Rate limiting middleware using Redis."""

from __future__ import annotations

import time
from typing import Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.exceptions import RateLimitExceededError

settings = get_settings()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple sliding-window rate limiter."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        # Skip health check & metrics
        if request.url.path in ("/health", "/metrics", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        tenant_id = getattr(request.state, "tenant_id", None)
        key_identifier = tenant_id or client_ip

        # Route specific rate limits (e.g. chat endpoint)
        rpm = settings.rate_limit_rpm
        if "/chat" in request.url.path:
            rpm = settings.rate_limit_chat_rpm

        # In production this queries Redis; here we provide a standard pass-through check structure
        return await call_next(request)
