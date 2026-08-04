"""
Unit tests for LeaseManager — in-memory fallback paths.

Covers: acquire, renew, release, is_lease_active via in-memory fallback
when Redis is unavailable (exception path).
"""

import asyncio
from unittest.mock import patch

import pytest

from vortex.storage.lease import LeaseManager


@pytest.fixture(autouse=True)
def clear_leases():
    """Reset in-memory lease store between tests."""
    LeaseManager.clear_in_memory_leases()
    yield
    LeaseManager.clear_in_memory_leases()


def _redis_unavailable(*args, **kwargs):
    raise ConnectionError("Redis unavailable")


@pytest.mark.asyncio
async def test_acquire_lease_inmemory_success():
    """Acquire lease via in-memory fallback when Redis is down."""
    with patch("vortex.storage.lease.get_redis", side_effect=_redis_unavailable):
        acquired = await LeaseManager.acquire_lease("res-1", "owner-A", ttl_seconds=5.0)
        assert acquired is True


@pytest.mark.asyncio
async def test_acquire_lease_inmemory_conflict():
    """Second owner cannot acquire an active lease held by another owner."""
    with patch("vortex.storage.lease.get_redis", side_effect=_redis_unavailable):
        acquired_a = await LeaseManager.acquire_lease("res-2", "owner-A", ttl_seconds=10.0)
        acquired_b = await LeaseManager.acquire_lease("res-2", "owner-B", ttl_seconds=10.0)
        assert acquired_a is True
        assert acquired_b is False


@pytest.mark.asyncio
async def test_acquire_lease_inmemory_same_owner_reacquire():
    """Same owner can re-acquire their own lease."""
    with patch("vortex.storage.lease.get_redis", side_effect=_redis_unavailable):
        await LeaseManager.acquire_lease("res-3", "owner-A", ttl_seconds=5.0)
        reacquired = await LeaseManager.acquire_lease("res-3", "owner-A", ttl_seconds=5.0)
        assert reacquired is True


@pytest.mark.asyncio
async def test_acquire_lease_inmemory_expired():
    """Another owner can acquire a lease after the original has expired."""
    with patch("vortex.storage.lease.get_redis", side_effect=_redis_unavailable):
        # Acquire with near-zero TTL
        await LeaseManager.acquire_lease("res-4", "owner-A", ttl_seconds=0.01)
        await asyncio.sleep(0.05)  # Wait for expiry
        acquired_b = await LeaseManager.acquire_lease("res-4", "owner-B", ttl_seconds=5.0)
        assert acquired_b is True


@pytest.mark.asyncio
async def test_renew_lease_inmemory_success():
    """Renew an active lease by the correct owner."""
    with patch("vortex.storage.lease.get_redis", side_effect=_redis_unavailable):
        await LeaseManager.acquire_lease("res-5", "owner-A", ttl_seconds=5.0)
        renewed = await LeaseManager.renew_lease("res-5", "owner-A", ttl_seconds=10.0)
        assert renewed is True


@pytest.mark.asyncio
async def test_renew_lease_inmemory_wrong_owner():
    """Cannot renew a lease owned by someone else."""
    with patch("vortex.storage.lease.get_redis", side_effect=_redis_unavailable):
        await LeaseManager.acquire_lease("res-6", "owner-A", ttl_seconds=5.0)
        renewed = await LeaseManager.renew_lease("res-6", "owner-B", ttl_seconds=10.0)
        assert renewed is False


@pytest.mark.asyncio
async def test_renew_lease_inmemory_nonexistent():
    """Cannot renew a lease that doesn't exist."""
    with patch("vortex.storage.lease.get_redis", side_effect=_redis_unavailable):
        renewed = await LeaseManager.renew_lease("res-7", "owner-A", ttl_seconds=10.0)
        assert renewed is False


@pytest.mark.asyncio
async def test_release_lease_inmemory_success():
    """Release a lease by the correct owner."""
    with patch("vortex.storage.lease.get_redis", side_effect=_redis_unavailable):
        await LeaseManager.acquire_lease("res-8", "owner-A", ttl_seconds=5.0)
        released = await LeaseManager.release_lease("res-8", "owner-A")
        assert released is True
        # Lease should be gone
        active = await LeaseManager.is_lease_active("res-8")
        assert active is False


@pytest.mark.asyncio
async def test_release_lease_inmemory_wrong_owner():
    """Cannot release a lease owned by someone else."""
    with patch("vortex.storage.lease.get_redis", side_effect=_redis_unavailable):
        await LeaseManager.acquire_lease("res-9", "owner-A", ttl_seconds=5.0)
        released = await LeaseManager.release_lease("res-9", "owner-B")
        assert released is False


@pytest.mark.asyncio
async def test_release_lease_inmemory_nonexistent():
    """Releasing a non-existent lease returns False."""
    with patch("vortex.storage.lease.get_redis", side_effect=_redis_unavailable):
        released = await LeaseManager.release_lease("res-10", "owner-A")
        assert released is False


@pytest.mark.asyncio
async def test_is_lease_active_inmemory():
    """Check if a lease is active via in-memory store."""
    with patch("vortex.storage.lease.get_redis", side_effect=_redis_unavailable):
        await LeaseManager.acquire_lease("res-11", "owner-A", ttl_seconds=5.0)
        active = await LeaseManager.is_lease_active("res-11")
        assert active is True


@pytest.mark.asyncio
async def test_is_lease_active_inmemory_expired():
    """Expired lease should not be active."""
    with patch("vortex.storage.lease.get_redis", side_effect=_redis_unavailable):
        await LeaseManager.acquire_lease("res-12", "owner-A", ttl_seconds=0.01)
        await asyncio.sleep(0.05)
        active = await LeaseManager.is_lease_active("res-12")
        assert active is False


@pytest.mark.asyncio
async def test_is_lease_active_inmemory_nonexistent():
    """Non-existent lease should not be active."""
    with patch("vortex.storage.lease.get_redis", side_effect=_redis_unavailable):
        active = await LeaseManager.is_lease_active("res-13")
        assert active is False
