import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any
from fastapi import FastAPI, Request, Response, Depends, HTTPException, status
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.logging import (
    CorrelationIdMiddleware,
    get_correlation_id,
    SensitiveDataRedactor,
    setup_structured_logging,
)
from app.api.v1.router import api_router
from app.database.session import Base, engine
import app.models.entities  # noqa: F401

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_structured_logging(log_level="DEBUG" if settings.DEBUG else "INFO")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        print(f"Database auto-creation notice: {e}")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="VyaparShield & NexusOps AI — Financial Intelligence & Operational Platform for Indian MSMEs.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Correlation ID Middleware (outermost)
app.add_middleware(CorrelationIdMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Centralized Safe Exception Handlers
# -----------------------------------------------------------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    cid = get_correlation_id()
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "correlation_id": cid,
        },
        headers=getattr(exc, "headers", None) or {},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    cid = get_correlation_id()
    safe_errors = SensitiveDataRedactor.redact_dict({"errors": exc.errors()})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "detail": "Request validation failed.",
            "errors": safe_errors.get("errors", []),
            "correlation_id": cid,
        },
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    cid = get_correlation_id()
    logging.getLogger("app.database").error(
        f"Database error during {request.method} {request.url.path}: {str(exc)}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal database error occurred. Reference correlation ID in support requests.",
            "correlation_id": cid,
        },
    )


@app.exception_handler(Exception)
async def global_unhandled_exception_handler(request: Request, exc: Exception):
    cid = get_correlation_id()
    logging.getLogger("app.server").error(
        f"Unhandled server error on {request.method} {request.url.path}: {str(exc)}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error occurred. Reference correlation ID in support requests.",
            "correlation_id": cid,
        },
    )


# Mount Versioned API Router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str


class ReadinessResponse(BaseModel):
    status: str
    dependencies: Dict[str, str]


# Dependency probes for readiness checks (mockable in automated test suites)
async def get_db_health() -> tuple[bool, str]:
    try:
        async with engine.connect() as conn:
            await asyncio.wait_for(conn.execute(text("SELECT 1")), timeout=settings.DB_TIMEOUT_SECONDS)
        return True, "healthy"
    except Exception as e:
        return False, f"unhealthy: {type(e).__name__}"


async def get_redis_health() -> tuple[bool, str]:
    if not settings.REDIS_URL:
        return True, "not_configured"
    try:
        import redis.asyncio as aioredis
        client = aioredis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=settings.REDIS_TIMEOUT_SECONDS,
            socket_timeout=settings.REDIS_TIMEOUT_SECONDS,
        )
        pong = await asyncio.wait_for(client.ping(), timeout=settings.REDIS_TIMEOUT_SECONDS)
        await client.aclose()
        return (True, "healthy") if pong else (False, "unhealthy: ping failed")
    except Exception as e:
        return False, f"unhealthy: {type(e).__name__}"


@app.get(
    "/healthz",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Liveness check probe",
)
async def healthz() -> HealthResponse:
    """Lightweight liveness check (does not test external network dependencies)."""
    return HealthResponse(
        status="healthy",
        service="nexusops-backend",
        version="1.0.0",
        environment=settings.APP_ENV,
    )


@app.get(
    "/readyz",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Readiness check probe",
)
async def readyz(
    response: Response,
    db_health: tuple[bool, str] = Depends(get_db_health),
    redis_health: tuple[bool, str] = Depends(get_redis_health),
) -> ReadinessResponse:
    """Deep readiness probe verifying database connectivity and required dependencies."""
    db_ok, db_msg = db_health
    redis_ok, redis_msg = redis_health

    dependencies_status = {
        "database": db_msg,
        "redis": redis_msg,
    }

    # Evaluate overall readiness
    is_ready = db_ok
    if settings.REQUIRE_REDIS_READY and not redis_ok:
        is_ready = False

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(
            status="unhealthy",
            dependencies=dependencies_status,
        )

    return ReadinessResponse(
        status="ready",
        dependencies=dependencies_status,
    )


from pathlib import Path
from fastapi.responses import HTMLResponse

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


@app.get(
    "/dashboard",
    response_class=HTMLResponse,
    tags=["Dashboard"],
    summary="Executive Visual Dashboard for VyaparShield",
)
async def dashboard_view():
    dashboard_file = TEMPLATE_DIR / "dashboard.html"
    if dashboard_file.exists():
        return HTMLResponse(content=dashboard_file.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Dashboard template not found.</h1>", status_code=404)


@app.get(
    "/",
    tags=["Root"],
    summary="Root entry point",
)
async def root() -> Dict[str, Any]:
    return {
        "message": "Welcome to VyaparShield / NexusOps AI API",
        "version": "1.0.0",
        "dashboard": "/dashboard",
        "docs": "/docs",
        "health": "/healthz",
        "api_v1": settings.API_V1_PREFIX,
    }
