"""
Integration tests for WorkflowWorker, TaskScheduler, and Dead Letter Queue (DLQ).
"""

import uuid

import pytest

from vortex.engine.worker import WorkflowWorker
from vortex.storage.database import get_session
from vortex.storage.models import WorkflowRun


@pytest.mark.integration
@pytest.mark.asyncio
async def test_worker_task_processing_and_dlq(async_client, monkeypatch):
    class MockRedis:
        async def xadd(self, key, message):
            return "1700000000000-0"

    monkeypatch.setattr("vortex.engine.scheduler.get_redis", lambda: MockRedis())

    run_id = uuid.uuid4()
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    # Pre-populate DB checkpoint
    async with get_session() as session:
        run = WorkflowRun(
            id=run_id,
            tenant_id=tenant_id,
            status="PENDING",
            input={},
            checkpoint={
                "run_id": str(run_id),
                "tenant_id": str(tenant_id),
                "status": "PENDING",
                "completed_nodes": {},
                "variables": {
                    "_dag": {
                        "name": "worker-dag",
                        "version": 1,
                        "nodes": [{"id": "w1", "type": "llm", "config": {"prompt": "Worker test"}}],
                    }
                },
            },
        )
        session.add(run)

    worker = WorkflowWorker()
    success = await worker.process_task({"run_id": str(run_id), "tenant_id": str(tenant_id)})
    assert success is True

    # Test retry & DLQ dispatch logic
    dlq_data = {"run_id": str(run_id), "tenant_id": str(tenant_id)}
    await worker.handle_retry_or_dlq(dlq_data, error="Execution timeout", attempt=3, max_attempts=3)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_worker_run_loop(async_client):
    worker = WorkflowWorker()
    await worker.run_loop(poll_interval_seconds=0.01, max_iterations=1)
    assert worker.running is True
