import pytest
import sys
import os
from httpx import AsyncClient, ASGITransport

# Ensure backend directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../backend")))

from app.main import app


@pytest.mark.asyncio
async def test_healthz_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "nexusops-backend"
        assert "version" in data
        assert "environment" in data


@pytest.mark.asyncio
async def test_readyz_healthy():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/readyz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "database" in data["dependencies"]
        assert "redis" in data["dependencies"]
        assert "X-Request-ID" in response.headers


@pytest.mark.asyncio
async def test_readyz_unhealthy_when_database_fails():
    from app.main import get_db_health
    
    async def failing_db():
        return False, "unhealthy: OperationalError"

    app.dependency_overrides[get_db_health] = failing_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/readyz")
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy"
            assert "unhealthy" in data["dependencies"]["database"]
    finally:
        app.dependency_overrides.pop(get_db_health, None)


@pytest.mark.asyncio
async def test_readyz_unhealthy_when_required_redis_fails():
    from app.main import get_redis_health, settings
    
    async def failing_redis():
        return False, "unhealthy: ConnectionRefusedError"

    old_setting = settings.REQUIRE_REDIS_READY
    settings.REQUIRE_REDIS_READY = True
    app.dependency_overrides[get_redis_health] = failing_redis
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/readyz")
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy"
            assert "unhealthy" in data["dependencies"]["redis"]
    finally:
        settings.REQUIRE_REDIS_READY = old_setting
        app.dependency_overrides.pop(get_redis_health, None)


@pytest.mark.asyncio
async def test_root_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["docs"] == "/docs"
        assert data["health"] == "/healthz"
