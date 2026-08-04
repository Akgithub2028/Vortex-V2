"""
Unit tests for WorkflowWorker — process_task, handle_retry_or_dlq, run_loop.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vortex.engine.state import WorkflowState, WorkflowStatus
from vortex.engine.worker import WorkflowWorker


@pytest.fixture
def worker():
    return WorkflowWorker(consumer_group="test-group", consumer_name="test-worker-1")


@pytest.mark.asyncio
async def test_process_task_missing_run_id(worker):
    """Task with missing run_id should return False."""
    result = await worker.process_task({"tenant_id": str(uuid.uuid4())})
    assert result is False


@pytest.mark.asyncio
async def test_process_task_lease_not_acquired(worker):
    """If lease is held by another worker, process_task returns True (skip)."""
    run_id = str(uuid.uuid4())
    with patch("vortex.storage.lease.LeaseManager.acquire_lease", new_callable=AsyncMock) as mock_acquire:
        mock_acquire.return_value = False
        result = await worker.process_task({"run_id": run_id, "tenant_id": str(uuid.uuid4())})
        assert result is True


@pytest.mark.asyncio
async def test_process_task_checkpoint_not_found(worker):
    """Missing checkpoint should return False."""
    run_id = str(uuid.uuid4())
    with patch("vortex.storage.lease.LeaseManager.acquire_lease", new_callable=AsyncMock, return_value=True), \
         patch("vortex.storage.lease.LeaseManager.release_lease", new_callable=AsyncMock, return_value=True), \
         patch("vortex.engine.worker.CheckpointStore") as mock_cp:
        mock_cp.load_checkpoint = AsyncMock(return_value=None)
        result = await worker.process_task({"run_id": run_id, "tenant_id": str(uuid.uuid4())})
        assert result is False


@pytest.mark.asyncio
async def test_process_task_terminal_state(worker):
    """Workflow already completed should return True."""
    run_id = uuid.uuid4()
    state = WorkflowState(
        run_id=run_id,
        tenant_id=uuid.uuid4(),
        status=WorkflowStatus.COMPLETED,
    )
    with patch("vortex.storage.lease.LeaseManager.acquire_lease", new_callable=AsyncMock, return_value=True), \
         patch("vortex.storage.lease.LeaseManager.release_lease", new_callable=AsyncMock, return_value=True), \
         patch("vortex.engine.worker.CheckpointStore") as mock_cp:
        mock_cp.load_checkpoint = AsyncMock(return_value=state)
        result = await worker.process_task({"run_id": str(run_id), "tenant_id": str(uuid.uuid4())})
        assert result is True


@pytest.mark.asyncio
async def test_process_task_missing_dag(worker):
    """Missing _dag in state variables should return False."""
    run_id = uuid.uuid4()
    state = WorkflowState(
        run_id=run_id,
        tenant_id=uuid.uuid4(),
        status=WorkflowStatus.RUNNING,
        variables={},
    )
    with patch("vortex.storage.lease.LeaseManager.acquire_lease", new_callable=AsyncMock, return_value=True), \
         patch("vortex.storage.lease.LeaseManager.release_lease", new_callable=AsyncMock, return_value=True), \
         patch("vortex.engine.worker.CheckpointStore") as mock_cp:
        mock_cp.load_checkpoint = AsyncMock(return_value=state)
        result = await worker.process_task({"run_id": str(run_id), "tenant_id": str(uuid.uuid4())})
        assert result is False


@pytest.mark.asyncio
async def test_process_task_execution_error(worker):
    """Unhandled error during execution returns False."""
    run_id = uuid.uuid4()
    dag_dict = {"name": "test", "version": 1, "nodes": []}
    state = WorkflowState(
        run_id=run_id,
        tenant_id=uuid.uuid4(),
        status=WorkflowStatus.RUNNING,
        variables={"_dag": dag_dict},
    )
    with patch("vortex.storage.lease.LeaseManager.acquire_lease", new_callable=AsyncMock, return_value=True), \
         patch("vortex.storage.lease.LeaseManager.release_lease", new_callable=AsyncMock, return_value=True), \
         patch("vortex.engine.worker.CheckpointStore") as mock_cp, \
         patch("vortex.engine.worker.DAGExecutor") as mock_exec:
        mock_cp.load_checkpoint = AsyncMock(return_value=state)
        mock_exec_instance = MagicMock()
        mock_exec_instance.run = AsyncMock(side_effect=RuntimeError("Boom"))
        mock_exec.return_value = mock_exec_instance
        result = await worker.process_task({"run_id": str(run_id), "tenant_id": str(uuid.uuid4())})
        assert result is False


@pytest.mark.asyncio
async def test_process_task_success(worker):
    """Successful execution returns True."""
    run_id = uuid.uuid4()
    dag_dict = {"name": "test", "version": 1, "nodes": []}
    state = WorkflowState(
        run_id=run_id,
        tenant_id=uuid.uuid4(),
        status=WorkflowStatus.RUNNING,
        variables={"_dag": dag_dict},
    )
    final_state = state.model_copy()
    final_state.status = WorkflowStatus.COMPLETED

    with patch("vortex.storage.lease.LeaseManager.acquire_lease", new_callable=AsyncMock, return_value=True), \
         patch("vortex.storage.lease.LeaseManager.release_lease", new_callable=AsyncMock, return_value=True), \
         patch("vortex.engine.worker.CheckpointStore") as mock_cp, \
         patch("vortex.engine.worker.DAGExecutor") as mock_exec:
        mock_cp.load_checkpoint = AsyncMock(return_value=state)
        mock_exec_instance = MagicMock()
        mock_exec_instance.run = AsyncMock(return_value=final_state)
        mock_exec.return_value = mock_exec_instance
        result = await worker.process_task({"run_id": str(run_id), "tenant_id": str(uuid.uuid4())})
        assert result is True


@pytest.mark.asyncio
async def test_handle_retry_with_backoff(worker):
    """Retry should re-enqueue task with delay."""
    run_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    task_data = {"run_id": str(run_id), "tenant_id": str(tenant_id)}

    with patch("vortex.engine.worker.TaskScheduler") as mock_sched, \
         patch("vortex.engine.worker.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        mock_sched.enqueue_workflow = AsyncMock()
        await worker.handle_retry_or_dlq(task_data, error="timeout", attempt=1, max_attempts=3)
        mock_sleep.assert_called_once_with(1.0)
        mock_sched.enqueue_workflow.assert_called_once()


@pytest.mark.asyncio
async def test_handle_dlq_after_max_attempts(worker):
    """After exhausting retries, task goes to DLQ."""
    run_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    task_data = {"run_id": str(run_id), "tenant_id": str(tenant_id)}

    with patch("vortex.engine.worker.TaskScheduler") as mock_sched:
        mock_sched.enqueue_dlq = AsyncMock()
        await worker.handle_retry_or_dlq(task_data, error="fatal", attempt=3, max_attempts=3)
        mock_sched.enqueue_dlq.assert_called_once()


@pytest.mark.asyncio
async def test_run_loop_with_max_iterations(worker):
    """run_loop should exit after max_iterations."""
    with patch("vortex.engine.worker.CheckpointStore") as mock_cp, \
         patch("vortex.engine.worker.asyncio.sleep", new_callable=AsyncMock):
        mock_cp.recover_orphaned_workflows = AsyncMock(return_value=[])
        await worker.run_loop(poll_interval_seconds=0.01, max_iterations=2)
        assert mock_cp.recover_orphaned_workflows.call_count == 2


@pytest.mark.asyncio
async def test_run_loop_orphan_recovery_error(worker):
    """run_loop should handle errors during orphan recovery gracefully."""
    with patch("vortex.engine.worker.CheckpointStore") as mock_cp, \
         patch("vortex.engine.worker.asyncio.sleep", new_callable=AsyncMock):
        mock_cp.recover_orphaned_workflows = AsyncMock(side_effect=RuntimeError("DB error"))
        await worker.run_loop(poll_interval_seconds=0.01, max_iterations=1)
        # Should complete without raising
