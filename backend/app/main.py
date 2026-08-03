"""
FastAPI application factory and startup lifecycle.

Architecture:
- Routers are registered with version prefix /api/v1
- Global exception handler converts PlatformException → structured JSON
- Prometheus metrics exposed at /metrics
- OpenTelemetry tracing enabled when OTEL_ENABLED=true
- Structured request logging via middleware
- Tenant isolation enforced by TenantMiddleware
"""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, ORJSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.exceptions import PlatformException
from app.core.logging import configure_logging, get_logger
from app.db.session import engine

settings = get_settings()

# Configure logging immediately on module import
configure_logging(
    log_level=settings.obs.log_level,
    log_format=settings.obs.log_format,
)

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────
# Application Lifespan
# ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage application startup and shutdown lifecycle.

    Startup:
    - Log application start
    - Run database bootstrap (create superadmin if not exists)

    Shutdown:
    - Dispose database connection pool
    """
    logger.info(
        "Starting Text-to-SQL Platform",
        version=settings.app_version,
        environment=settings.environment,
    )

    # Bootstrap superadmin on first run
    try:
        from app.db.session import AsyncSessionLocal
        from app.services.bootstrap import BootstrapService
        async with AsyncSessionLocal() as session:
            await BootstrapService(session).run()
    except Exception as exc:
        logger.warning("Bootstrap skipped or failed", error=str(exc))

    logger.info("Application startup complete")

    yield

    # Cleanup
    await engine.dispose()
    logger.info("Application shutdown complete")


# ─────────────────────────────────────────────────────────────
# Application Factory
# ─────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Multi-Tenant Text-to-SQL and Document Chat Platform API. "
            "Provides secure, tenant-isolated natural language querying "
            "over databases and documents."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time"],
    )

    # ── Request ID + Timing Middleware ────────────────────────
    app.add_middleware(RequestContextMiddleware)

    # ── Rate Limiting Middleware ───────────────────────────────
    if settings.rate_limit_enabled:
        from app.middleware.rate_limit import RateLimitMiddleware
        app.add_middleware(RateLimitMiddleware)

    # ── Prometheus Instrumentation ────────────────────────────
    Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/health", "/metrics", "/docs", "/redoc", "/openapi.json"],
        inprogress_labels=True,
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

    # ── OpenTelemetry ─────────────────────────────────────────
    if settings.obs.otel_enabled:
        _configure_otel(app)

    # ── Exception Handlers ────────────────────────────────────
    _register_exception_handlers(app)

    # ── API Routers ───────────────────────────────────────────
    _register_routers(app)

    return app


# ─────────────────────────────────────────────────────────────
# Middleware
# ─────────────────────────────────────────────────────────────

class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Inject request_id, process timing, and structured logging context
    into every request.
    """

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        request_id = str(uuid.uuid4())
        start_time = time.perf_counter()

        # Make request_id available via request.state
        request.state.request_id = request_id

        # Bind context vars for structlog
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=_get_client_ip(request),
        )

        response = await call_next(request)

        process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time_ms)

        logger.info(
            "Request completed",
            status_code=response.status_code,
            process_time_ms=process_time_ms,
        )

        return response


def _get_client_ip(request: Request) -> str:
    """Extract real client IP respecting X-Forwarded-For."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ─────────────────────────────────────────────────────────────
# Exception Handlers
# ─────────────────────────────────────────────────────────────

def _register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers."""

    @app.exception_handler(PlatformException)
    async def platform_exception_handler(
        request: Request, exc: PlatformException
    ) -> JSONResponse:
        """Convert PlatformException to a structured JSON response."""
        logger.warning(
            "Platform exception",
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
        )
        return ORJSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "details": exc.details,
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Convert Pydantic validation errors to structured JSON."""
        errors = [
            {
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
            for error in exc.errors()
        ]
        return ORJSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed.",
                    "details": {"errors": errors},
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Catch-all handler — never expose stack traces in production."""
        logger.exception("Unhandled exception", exc_info=exc)
        return ORJSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred. Please try again.",
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )


# ─────────────────────────────────────────────────────────────
# Router Registration
# ─────────────────────────────────────────────────────────────

def _register_routers(app: FastAPI) -> None:
    """Import and register all API routers."""
    from app.api.v1.routers.auth import router as auth_router
    from app.api.v1.routers.users import router as users_router
    from app.api.v1.routers.roles import router as roles_router
    from app.api.v1.routers.connections import router as connections_router
    from app.api.v1.routers.knowledge_bases import router as kb_router
    from app.api.v1.routers.conversations import router as conv_router
    from app.api.v1.routers.chat import router as chat_router

    API_PREFIX = "/api/v1"

    app.include_router(auth_router, prefix=f"{API_PREFIX}/auth", tags=["Authentication"])
    app.include_router(users_router, prefix=f"{API_PREFIX}/users", tags=["Users"])
    app.include_router(roles_router, prefix=f"{API_PREFIX}/roles", tags=["Roles & Permissions"])
    app.include_router(connections_router, prefix=f"{API_PREFIX}/connections", tags=["Database Connections"])
    app.include_router(kb_router, prefix=f"{API_PREFIX}/knowledge-bases", tags=["Knowledge Bases"])
    app.include_router(conv_router, prefix=f"{API_PREFIX}/conversations", tags=["Conversations"])
    app.include_router(chat_router, prefix=f"{API_PREFIX}/chat", tags=["Chat"])


# ─────────────────────────────────────────────────────────────
# OpenTelemetry Setup
# ─────────────────────────────────────────────────────────────

def _configure_otel(app: FastAPI) -> None:
    """Configure OpenTelemetry tracing when enabled."""
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": settings.obs.otel_service_name})
        provider = TracerProvider(resource=resource)

        exporter = OTLPSpanExporter(endpoint=settings.obs.otel_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))

        trace.set_tracer_provider(provider)

        FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
        SQLAlchemyInstrumentor().instrument()

        logger.info("OpenTelemetry tracing enabled", endpoint=settings.obs.otel_endpoint)
    except Exception as exc:
        logger.warning("OpenTelemetry setup failed", error=str(exc))


# ─────────────────────────────────────────────────────────────
# Health Check & UI Endpoints
# ─────────────────────────────────────────────────────────────

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# Create the app instance
app = create_app()

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", include_in_schema=False)
async def serve_ui():
    """Serve the Web Application UI dashboard."""
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "NexusAI Platform API is running. Go to /docs for OpenAPI documentation."}

@app.get("/health", include_in_schema=False)
async def health_check() -> dict[str, str]:
    """
    Lightweight health check endpoint for load balancers and Docker.

    Returns 200 OK if the application is running.
    Does NOT check downstream dependencies (DB, Redis) to avoid cascading failures.
    """
    return {"status": "healthy", "version": settings.app_version}

