"""
Deterministic Fault Injection and Chaos Simulation Test Suite for Vortex Engine.
"""

import asyncio
from unittest.mock import AsyncMock, patch
import pytest
import uuid

from vortex.engine.checkpoint import CheckpointStore
from vortex.engine.event_store import EventStore
from vortex.engine.executor import DynamicGraphExecutor
from vortex.engine.state import DAGDefinition, NodeDefinition, WorkflowState, WorkflowStatus
from vortex.engine.worker import WorkflowWorker
from vortex.storage.database import init_db
from vortex.storage.lease import LeaseManager


@pytest.mark.asyncio
async def test_lease_manager_mutual_exclusion_and_ttl():
    LeaseManager.clear_in_memory_leases()
    run_id = str(uuid.uuid4())

    # Worker 1 acquires lease for 0.2s
    acq1 = await LeaseManager.acquire_lease(run_id, owner_id="worker-1", ttl_seconds=0.2)
    assert acq1 is True

    # Worker 2 attempts to acquire lease immediately -> should be blocked
    acq2 = await LeaseManager.acquire_lease(run_id, owner_id="worker-2", ttl_seconds=0.2)
    assert acq2 is False

    # Wait for TTL to expire
    await asyncio.sleep(0.25)

    # Worker 2 acquires lease after TTL expiry
    acq3 = await LeaseManager.acquire_lease(run_id, owner_id="worker-2", ttl_seconds=0.5)
    assert acq3 is True

    # Worker 2 releases lease
    rel = await LeaseManager.release_lease(run_id, owner_id="worker-2")
    assert rel is True


@pytest.mark.asyncio
async def test_fault_injection_worker_crash_and_recovery():
    await init_db()
    EventStore.clear_cache()
    LeaseManager.clear_in_memory_leases()

    tenant_id = uuid.uuid4()
    run_id = uuid.uuid4()

    dag = DAGDefinition(
        name="resilient-pipeline",
        nodes=[
            NodeDefinition(id="step1", type="tool", config={"tool_name": "python_eval", "tool_args": {"expression": "1+1"}}),
            NodeDefinition(id="step2", type="llm", config={"prompt": "Hello"}, dependencies=["step1"]),
        ],
    )

    # Save initial checkpoint
    initial_state = WorkflowState(
        run_id=run_id,
        tenant_id=tenant_id,
        variables={"_dag": dag.model_dump(mode="json")},
    )
    await CheckpointStore.save_checkpoint(initial_state)

    # Worker 1 starts task, completes step 1, but crashes mid-execution (leaving status RUNNING)
    worker1_lease = await LeaseManager.acquire_lease(str(run_id), owner_id="worker-crash-test-1", ttl_seconds=0.1)
    assert worker1_lease is True

    # Simulate step1 completing and checkpoint saving before crash
    initial_state.status = WorkflowStatus.RUNNING
    initial_state.completed_nodes["step1"] = {"val": 2}
    await CheckpointStore.save_checkpoint(initial_state)

    # Simulate process crash: lease expires naturally
    await asyncio.sleep(0.15)
    active = await LeaseManager.is_lease_active(str(run_id))
    assert active is False

    # Worker 2 picks up orphaned task and resumes execution
    task_payload = {"run_id": str(run_id), "tenant_id": str(tenant_id)}
    worker2 = WorkflowWorker(consumer_name="worker-recovery-test-2")

    with patch("vortex.engine.nodes.tool_node.ToolNode.execute", new_callable=AsyncMock) as mock_tool2:
        with patch("vortex.engine.nodes.llm_node.LLMNode.execute", new_callable=AsyncMock) as mock_llm2:
            mock_llm2.return_value = {"text": "Hello response"}

            success2 = await worker2.process_task(task_payload)
            assert success2 is True

            # Verify step1 was NOT re-executed (skipped because completed in checkpoint)
            mock_tool2.assert_not_called()
            mock_llm2.assert_called_once()

    # Final state check
    final_state = await CheckpointStore.load_checkpoint(run_id)
    assert final_state.status == WorkflowStatus.COMPLETED
    assert "step1" in final_state.completed_nodes
    assert "step2" in final_state.completed_nodes
