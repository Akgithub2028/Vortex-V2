"""
Unit tests for CheckpointStore persistence and orphan recovery logic.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from vortex.engine.checkpoint import CheckpointStore
from vortex.engine.state import WorkflowState, WorkflowStatus
from vortex.storage.database import get_session
from vortex.storage.models import WorkflowRun


@pytest.mark.asyncio
async def test_checkpoint_save_and_load(async_client):
    run_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    # Create run entry
    async with get_session() as session:
        run = WorkflowRun(
            id=run_id,
            tenant_id=tenant_id,
            status="PENDING",
            input={"test": 123},
        )
        session.add(run)

    state = WorkflowState(
        run_id=run_id,
        tenant_id=tenant_id,
        status=WorkflowStatus.RUNNING,
        variables={"step": 1},
    )

    await CheckpointStore.save_checkpoint(state)
    loaded_state = await CheckpointStore.load_checkpoint(run_id)

    assert loaded_state is not None
    assert loaded_state.run_id == run_id
    assert loaded_state.variables["step"] == 1
    assert loaded_state.status == WorkflowStatus.RUNNING


@pytest.mark.asyncio
async def test_recover_orphaned_workflows(async_client):
    run_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    old_time = datetime.now(timezone.utc) - timedelta(minutes=10)

    async with get_session() as session:
        run = WorkflowRun(
            id=run_id,
            tenant_id=tenant_id,
            status=WorkflowStatus.RUNNING.value,
            input={},
            heartbeat_at=old_time,
        )
        session.add(run)

    orphaned = await CheckpointStore.recover_orphaned_workflows()
    assert (run_id, tenant_id) in orphaned


@pytest.mark.asyncio
async def test_checkpoint_save_creates_new_run(async_client):
    """save_checkpoint should create a new WorkflowRun when none exists."""
    run_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    state = WorkflowState(
        run_id=run_id,
        tenant_id=tenant_id,
        status=WorkflowStatus.RUNNING,
        variables={"data": "test"},
    )

    # Clear cache to force DB path
    CheckpointStore._cache.clear()
    await CheckpointStore.save_checkpoint(state)

    # Verify it was created in DB
    async with get_session() as session:
        from sqlalchemy import select

        stmt = select(WorkflowRun).where(WorkflowRun.id == run_id)
        res = await session.execute(stmt)
        run = res.scalar_one_or_none()
        assert run is not None
        assert run.status == "RUNNING"


@pytest.mark.asyncio
async def test_checkpoint_load_nonexistent(async_client):
    """load_checkpoint should return None for a non-existent run_id."""
    CheckpointStore._cache.clear()
    state = await CheckpointStore.load_checkpoint(uuid.uuid4())
    assert state is None


@pytest.mark.asyncio
async def test_checkpoint_load_by_string_id(async_client):
    """load_checkpoint should accept string run_id."""
    run_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    async with get_session() as session:
        run = WorkflowRun(
            id=run_id,
            tenant_id=tenant_id,
            status="PENDING",
            input={},
            checkpoint=WorkflowState(
                run_id=run_id,
                tenant_id=tenant_id,
                status=WorkflowStatus.PENDING,
            ).model_dump(mode="json"),
        )
        session.add(run)

    CheckpointStore._cache.clear()
    state = await CheckpointStore.load_checkpoint(str(run_id))
    assert state is not None
    assert state.run_id == run_id


@pytest.mark.asyncio
async def test_checkpoint_update_heartbeat(async_client):
    """update_heartbeat should update the cache and DB record."""
    run_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    async with get_session() as session:
        run = WorkflowRun(
            id=run_id,
            tenant_id=tenant_id,
            status="RUNNING",
            input={},
        )
        session.add(run)

    state = WorkflowState(
        run_id=run_id,
        tenant_id=tenant_id,
        status=WorkflowStatus.RUNNING,
    )
    CheckpointStore._cache[str(run_id)] = state

    old_updated = state.updated_at
    await CheckpointStore.update_heartbeat(run_id)
    assert CheckpointStore._cache[str(run_id)].updated_at >= old_updated


@pytest.mark.asyncio
async def test_checkpoint_save_terminal_sets_completed_at(async_client):
    """save_checkpoint should set completed_at for terminal workflows."""
    run_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    async with get_session() as session:
        run = WorkflowRun(
            id=run_id,
            tenant_id=tenant_id,
            status="PENDING",
            input={},
        )
        session.add(run)

    state = WorkflowState(
        run_id=run_id,
        tenant_id=tenant_id,
        status=WorkflowStatus.COMPLETED,
    )

    await CheckpointStore.save_checkpoint(state)

    async with get_session() as session:
        from sqlalchemy import select

        stmt = select(WorkflowRun).where(WorkflowRun.id == run_id)
        res = await session.execute(stmt)
        run = res.scalar_one()
        assert run.completed_at is not None
