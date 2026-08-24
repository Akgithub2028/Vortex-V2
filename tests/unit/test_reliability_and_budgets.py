"""
Unit tests for step limits, node execution timeouts, and cost budget caps in DynamicGraphExecutor.
"""

from __future__ import annotations

import asyncio
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from vortex.api.errors import WorkflowBudgetExceededError, WorkflowMaxStepsExceededError
from vortex.engine.event_store import EventStore
from vortex.engine.executor import DynamicGraphExecutor
from vortex.engine.state import DAGDefinition, NodeDefinition, WorkflowState, WorkflowStatus
from vortex.storage.database import init_db


@pytest.mark.asyncio
async def test_budget_exceeded_error():
    """Workflow exceeding cost budget should be marked FAILED with budget error."""
    await init_db()
    EventStore.clear_cache()

    dag = DAGDefinition(
        name="budget-test",
        nodes=[NodeDefinition(id="n1", type="llm", config={"prompt": "test"})],
    )
    state = WorkflowState(
        run_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        variables={"max_budget_usd": 0.05},
    )
    # Pre-set cost above budget to trigger the gate immediately
    state.total_cost_usd = Decimal("0.10")

    executor = DynamicGraphExecutor(dag=dag, state=state)
    final_state = await executor.run()

    # The executor catches WorkflowBudgetExceededError and marks workflow FAILED
    assert final_state.status == WorkflowStatus.FAILED
    assert "exceeded budget limit" in final_state.variables.get("_workflow_error", "").lower() or \
           "budget" in final_state.variables.get("_workflow_error", "").lower()


@pytest.mark.asyncio
async def test_max_steps_exceeded_error():
    """Workflow exceeding max step count should be marked FAILED with steps error."""
    await init_db()
    EventStore.clear_cache()

    # Create a DAG with multiple nodes that exceeds max_steps=1
    dag = DAGDefinition(
        name="steps-test",
        nodes=[
            NodeDefinition(id="n1", type="llm", config={"prompt": "test1"}),
            NodeDefinition(id="n2", type="llm", config={"prompt": "test2"}),
            NodeDefinition(id="n3", type="llm", config={"prompt": "test3"}),
        ],
    )
    state = WorkflowState(
        run_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        variables={"max_steps": 1},  # Only allow 1 step, but DAG has 3 nodes
    )

    executor = DynamicGraphExecutor(dag=dag, state=state)

    with patch("vortex.engine.nodes.llm_node.LLMNode.execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {"text": "mocked output", "provider": "mock", "model": "mock"}
        final_state = await executor.run()

    # Executor catches WorkflowMaxStepsExceededError → marks FAILED
    assert final_state.status == WorkflowStatus.FAILED
    assert "step" in final_state.variables.get("_workflow_error", "").lower() or \
           "max" in final_state.variables.get("_workflow_error", "").lower()


@pytest.mark.asyncio
async def test_node_timeout_enforcement():
    """Node exceeding its timeout should trigger a failure."""
    await init_db()
    EventStore.clear_cache()

    node_def = NodeDefinition(
        id="slow1",
        type="llm",
        config={"prompt": "test", "timeout_seconds": 0.05},  # 50ms timeout
    )
    dag = DAGDefinition(name="timeout-test", nodes=[node_def])
    state = WorkflowState(
        run_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
    )

    executor = DynamicGraphExecutor(dag=dag, state=state)

    # Mock LLMNode.execute to sleep longer than the timeout
    async def slow_execute(*args, **kwargs):
        await asyncio.sleep(2.0)  # 2 seconds, well over the 50ms timeout
        return {"text": "should not reach here"}

    with patch("vortex.engine.nodes.llm_node.LLMNode.execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.side_effect = slow_execute
        final_state = await executor.run()

    # The node should have failed due to timeout (asyncio.wait_for raises TimeoutError)
    assert final_state.status == WorkflowStatus.FAILED
    assert "slow1" in final_state.failed_nodes
