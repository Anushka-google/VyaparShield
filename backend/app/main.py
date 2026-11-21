from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any

from app.core.config import get_settings
from app.api.v1.router import api_router
from app.database.session import Base, engine
import app.models.entities  # noqa: F401

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
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

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.get(
    "/healthz",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Liveness check probe",
)
async def healthz() -> HealthResponse:
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
    dependencies_status = {
        "database": "configured",
        "redis": "configured",
    }
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
