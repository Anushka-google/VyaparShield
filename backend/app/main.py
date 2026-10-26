from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any

from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="NexusOps AI — Production-grade Applied AI, Agentic AI, and DevSecOps Platform for MSME Finance & Incident Operations.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to frontend origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str


class ReadinessResponse(BaseModel):
    status: str
    dependencies: Dict[str, str]


@app.get(
    "/healthz",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Liveness check probe",
)
async def healthz() -> HealthResponse:
    """Liveness probe verifying that the HTTP server process is running."""
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
async def readyz() -> ReadinessResponse:
    """Readiness probe checking availability of core backing services (PostgreSQL, Redis)."""
    # In initial scaffolding, we report dependency targets; real connection probes will test live socket connections in Phase A1
    dependencies_status = {
        "database": "configured",
        "redis": "configured",
    }
    return ReadinessResponse(
        status="ready",
        dependencies=dependencies_status,
    )


@app.get(
    "/",
    tags=["Root"],
    summary="Root entry point",
)
async def root() -> Dict[str, Any]:
    return {
        "message": "Welcome to NexusOps AI API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/healthz",
    }
