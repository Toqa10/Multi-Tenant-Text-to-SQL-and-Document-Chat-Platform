"""Tenant isolation middleware."""

from __future__ import annotations

from typing import Any
import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.exceptions import TenantIsolationError
from app.core.security import decode_access_token

logger = structlog.get_logger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Extracts tenant context from JWT access token if present in request.
    Injects tenant_id into request.state and structlog context.
    """

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        tenant_id = None
        user_id = None

        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                payload = decode_access_token(token)
                user_id = payload.get("sub")
                tenant_id = payload.get("tenant_id")
            except Exception:
                pass  # Validation happens in route dependency

        request.state.tenant_id = tenant_id
        request.state.user_id = user_id

        if tenant_id:
            structlog.contextvars.bind_contextvars(
                tenant_id=str(tenant_id),
                user_id=str(user_id) if user_id else None,
            )

        return await call_next(request)
