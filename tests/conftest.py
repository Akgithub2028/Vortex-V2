"""
Pytest configuration and global fixtures for Vortex test suite.
"""

from __future__ import annotations

import os
from typing import AsyncGenerator
import uuid

from httpx import ASGITransport, AsyncClient
import pytest
from sqlalchemy import select

# Force testing environment before importing settings
os.environ["VORTEX_ENVIRONMENT"] = "testing"
os.environ["VORTEX_DATABASE_URL"] = "sqlite+aiosqlite:///file:memdb1?mode=memory&cache=shared&uri=true"
os.environ["VORTEX_REDIS_URL"] = "redis://localhost:6379/1"

from vortex.api.main import create_app
from vortex.config import get_settings
from vortex.storage.database import get_engine, get_session
from vortex.storage.models import Base, Tenant


@pytest.fixture(autouse=True)
def reset_settings():
    """Reset cached settings between test runs."""
    get_settings.cache_clear()


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Provide AsyncClient instance bound to the FastAPI app with initialized SQLite tables."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Ensure default dev tenant exists
    dev_tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    async with get_session() as session:
        result = await session.execute(select(Tenant).where(Tenant.id == dev_tenant_id))
        if not result.scalar_one_or_none():
            tenant = Tenant(id=dev_tenant_id, name="Default Dev Tenant")
            session.add(tenant)

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
