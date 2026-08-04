"""
Unit tests for API health and readiness endpoints.
"""

import pytest


@pytest.mark.asyncio
async def test_healthz_endpoint(async_client):
    response = await async_client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "vortex"


@pytest.mark.asyncio
async def test_readyz_endpoint(async_client, monkeypatch):
    class MockRedis:
        async def ping(self):
            return True

    monkeypatch.setattr("vortex.api.routes.health.get_redis", lambda: MockRedis())

    response = await async_client.get("/readyz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"] == "ok"
    assert data["redis"] == "ok"
