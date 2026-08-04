"""
Unit tests for storage layer (database, models, redis helpers).
"""

import uuid

import pytest
from sqlalchemy import select

import vortex.storage.redis as vortex_redis
from vortex.storage.database import get_engine, get_session
from vortex.storage.models import Tenant


@pytest.mark.asyncio
async def test_database_lifecycle_and_models(async_client):
    engine = get_engine()
    assert engine is not None

    async with get_session() as session:
        tenant_id = uuid.uuid4()
        tenant = Tenant(id=tenant_id, name="Test Tenant")
        session.add(tenant)

    async with get_session() as session:
        result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
        fetched = result.scalar_one_or_none()
        assert fetched is not None
        assert fetched.name == "Test Tenant"


@pytest.mark.asyncio
async def test_redis_helpers(monkeypatch):
    class MockLock:
        async def __aenter__(self):
            return True

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def acquire(self):
            return True

        async def release(self):
            pass

    class MockRedis:
        async def ping(self):
            return True

        async def aclose(self):
            pass

        def lock(self, name, timeout=10.0, blocking_timeout=5.0):
            return MockLock()

    mock_client = MockRedis()
    monkeypatch.setattr(vortex_redis, "_redis_client", mock_client)

    redis_client = vortex_redis.get_redis()
    assert await redis_client.ping() is True

    async with vortex_redis.lock("test_lock"):
        pass

    await vortex_redis.close_redis()


@pytest.mark.asyncio
async def test_init_redis_success(monkeypatch):
    """init_redis should verify connection with a ping."""

    class MockRedis:
        async def ping(self):
            return True

        async def aclose(self):
            pass

    monkeypatch.setattr(vortex_redis, "_redis_client", MockRedis())
    await vortex_redis.init_redis()


@pytest.mark.asyncio
async def test_close_redis_already_none(monkeypatch):
    """close_redis when client is already None should be a no-op."""
    monkeypatch.setattr(vortex_redis, "_redis_client", None)
    await vortex_redis.close_redis()
    assert vortex_redis._redis_client is None


@pytest.mark.asyncio
async def test_lock_release_failure(monkeypatch):
    """Lock release failure should be handled gracefully."""

    class MockLock:
        async def acquire(self):
            return True

        async def release(self):
            raise RuntimeError("Release failed")

    class MockRedis:
        def lock(self, name, timeout=10.0, blocking_timeout=5.0):
            return MockLock()

    monkeypatch.setattr(vortex_redis, "_redis_client", MockRedis())

    # Should not raise despite release failure
    async with vortex_redis.lock("test_fail_lock"):
        pass


@pytest.mark.asyncio
async def test_lock_not_acquired(monkeypatch):
    """When lock is not acquired, release should not be called."""

    class MockLock:
        async def acquire(self):
            return False

        async def release(self):
            raise AssertionError("Should not be called")

    class MockRedis:
        def lock(self, name, timeout=10.0, blocking_timeout=5.0):
            return MockLock()

    monkeypatch.setattr(vortex_redis, "_redis_client", MockRedis())

    async with vortex_redis.lock("test_no_acquire") as acquired:
        assert acquired is False


@pytest.mark.asyncio
async def test_database_close_lifecycle(async_client):
    """close_db should close the engine and reset the singleton."""
    from vortex.storage.database import close_db, get_engine

    engine = get_engine()
    assert engine is not None
    await close_db()
