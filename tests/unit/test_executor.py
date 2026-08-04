"""
Unit tests for Workflow DAG Executor and State Machine.
"""

import uuid

import pytest

from vortex.engine.executor import DAGExecutor
from vortex.engine.state import DAGDefinition, NodeDefinition, WorkflowState, WorkflowStatus


@pytest.mark.asyncio
async def test_dag_executor_simple_chain(monkeypatch):
    # Mock CheckpointStore to avoid DB calls during unit test
    async def mock_save(*args, **kwargs):
        pass

    monkeypatch.setattr("vortex.engine.checkpoint.CheckpointStore.save_checkpoint", mock_save)

    dag = DAGDefinition(
        name="test-dag",
        nodes=[
            NodeDefinition(id="node1", type="llm", config={"prompt": "Hello {topic}"}),
            NodeDefinition(id="node2", type="llm", dependencies=["node1"], config={"prompt": "Summarize"}),
        ],
    )

    state = WorkflowState(
        run_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        variables={"topic": "AI Systems"},
    )

    executor = DAGExecutor(dag, state)
    final_state = await executor.run()

    assert final_state.status == WorkflowStatus.COMPLETED
    assert "node1" in final_state.completed_nodes
    assert "node2" in final_state.completed_nodes
    assert final_state.total_tokens > 0


@pytest.mark.asyncio
async def test_dag_executor_circular_dependency_error():
    dag = DAGDefinition(
        name="circular-dag",
        nodes=[
            NodeDefinition(id="a", type="llm", dependencies=["b"]),
            NodeDefinition(id="b", type="llm", dependencies=["a"]),
        ],
    )
    state = WorkflowState(run_id=uuid.uuid4(), tenant_id=uuid.uuid4())
    with pytest.raises(ValueError, match="Circular dependency"):
        DAGExecutor(dag, state)
