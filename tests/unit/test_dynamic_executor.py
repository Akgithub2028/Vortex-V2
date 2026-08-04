"""
Unit tests for Vortex DynamicGraphExecutor and yield_task functionality.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from vortex.engine.event_store import EventStore
from vortex.engine.executor import DynamicGraphExecutor, yield_task
from vortex.engine.state import DAGDefinition, NodeDefinition, WorkflowState, WorkflowStatus
from vortex.storage.database import init_db


@pytest.mark.asyncio
async def test_dynamic_graph_yielding():
    await init_db()
    EventStore.clear_cache()

    tenant_id = uuid.uuid4()
    run_id = uuid.uuid4()

    # Define initial DAG with a single tool node that yields child LLM node
    dag = DAGDefinition(
        name="dynamic-pipeline",
        nodes=[
            NodeDefinition(
                id="root_tool",
                type="tool",
                config={"tool_name": "python_eval", "tool_args": {"expression": "2 + 2"}},
            )
        ],
    )

    state = WorkflowState(run_id=run_id, tenant_id=tenant_id)
    executor = DynamicGraphExecutor(dag, state)

    # Mock tool node execute to return yielded node
    with patch("vortex.engine.nodes.tool_node.ToolNode.execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {
            "val": 4,
            **yield_task("child_llm", "llm", {"prompt": "Explain 4"}, dependencies=["root_tool"]),
        }
        with patch("vortex.engine.nodes.llm_node.LLMNode.execute", new_callable=AsyncMock) as mock_llm_exec:
            mock_llm_exec.return_value = {"text": "4 is an even number"}

            final_state = await executor.run()

            assert final_state.status == WorkflowStatus.COMPLETED
            assert "root_tool" in final_state.completed_nodes
            assert "child_llm" in final_state.completed_nodes
            assert final_state.variables["text"] == "4 is an even number"

    events = await EventStore.get_events(run_id)
    event_types = [e.event_type for e in events]
    assert "WorkflowStarted" in event_types
    assert "NodeYielded" in event_types
    assert "WorkflowCompleted" in event_types


@pytest.mark.asyncio
async def test_dynamic_executor_hitl_pause():
    await init_db()
    tenant_id = uuid.uuid4()
    run_id = uuid.uuid4()

    dag = DAGDefinition(
        name="hitl-pipeline",
        nodes=[
            NodeDefinition(id="approve_step", type="human", config={"instructions": "Approve action"}),
            NodeDefinition(
                id="final_step", type="tool", config={"tool_name": "python_eval", "tool_args": {"expression": "10*10"}}, dependencies=["approve_step"]
            ),
        ],
    )

    state = WorkflowState(run_id=run_id, tenant_id=tenant_id)
    executor = DynamicGraphExecutor(dag, state)

    # Initial run should pause at human node
    paused_state = await executor.run()
    assert paused_state.status == WorkflowStatus.AWAITING_APPROVAL

    # Simulate human approval
    paused_state.status = WorkflowStatus.RUNNING
    paused_state.completed_nodes["approve_step"] = {"approved": True}

    # Resume execution
    resume_executor = DynamicGraphExecutor(dag, paused_state)
    final_state = await resume_executor.run()

    assert final_state.status == WorkflowStatus.COMPLETED
    assert "final_step" in final_state.completed_nodes


@pytest.mark.asyncio
async def test_executor_node_failure_marks_workflow_failed():
    """When a node raises an exception, the workflow should be marked FAILED."""
    await init_db()
    EventStore.clear_cache()

    dag = DAGDefinition(
        name="fail-pipeline",
        nodes=[
            NodeDefinition(
                id="bad_node",
                type="tool",
                config={
                    "tool_name": "python_eval",
                    "tool_args": {"expression": "1/0"},
                },
            ),
        ],
    )

    state = WorkflowState(run_id=uuid.uuid4(), tenant_id=uuid.uuid4())
    executor = DynamicGraphExecutor(dag, state)

    with patch("vortex.engine.nodes.tool_node.ToolNode.execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.side_effect = RuntimeError("Division by zero")
        final = await executor.run()
        assert final.status == WorkflowStatus.FAILED
        assert "bad_node" in final.failed_nodes


@pytest.mark.asyncio
async def test_executor_broken_deps_skip():
    """Nodes with broken dependencies should be skipped."""
    await init_db()
    EventStore.clear_cache()

    dag = DAGDefinition(
        name="skip-pipeline",
        nodes=[
            NodeDefinition(id="step1", type="llm", config={"prompt": "Hello"}),
            NodeDefinition(id="step2", type="llm", config={"prompt": "World"}, dependencies=["step1"]),
        ],
    )

    state = WorkflowState(run_id=uuid.uuid4(), tenant_id=uuid.uuid4())
    executor = DynamicGraphExecutor(dag, state)

    with patch("vortex.engine.nodes.llm_node.LLMNode.execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.side_effect = RuntimeError("Provider error")
        final = await executor.run()
        assert final.status == WorkflowStatus.FAILED
        assert "step1" in final.failed_nodes


@pytest.mark.asyncio
async def test_executor_cycle_detection():
    """DAG with circular dependencies should raise ValueError."""
    with pytest.raises(ValueError, match="Circular dependency"):
        dag = DAGDefinition(
            name="cyclic-dag",
            nodes=[
                NodeDefinition(id="a", type="llm", config={}, dependencies=["b"]),
                NodeDefinition(id="b", type="llm", config={}, dependencies=["a"]),
            ],
        )
        state = WorkflowState(run_id=uuid.uuid4(), tenant_id=uuid.uuid4())
        DynamicGraphExecutor(dag, state)


@pytest.mark.asyncio
async def test_executor_missing_dependency():
    """DAG referencing a missing dependency should raise ValueError."""
    with pytest.raises(ValueError, match="missing dependency"):
        dag = DAGDefinition(
            name="missing-dep",
            nodes=[
                NodeDefinition(id="step1", type="llm", config={}, dependencies=["nonexistent"]),
            ],
        )
        state = WorkflowState(run_id=uuid.uuid4(), tenant_id=uuid.uuid4())
        DynamicGraphExecutor(dag, state)


@pytest.mark.asyncio
async def test_executor_event_callback():
    """Event callback should be called during execution."""
    await init_db()
    EventStore.clear_cache()

    dag = DAGDefinition(
        name="callback-test",
        nodes=[
            NodeDefinition(id="n1", type="llm", config={"prompt": "Hi"}),
        ],
    )

    events_received = []

    def callback(event_type, payload):
        events_received.append(event_type)

    state = WorkflowState(run_id=uuid.uuid4(), tenant_id=uuid.uuid4())
    executor = DynamicGraphExecutor(dag, state)
    final = await executor.run(event_callback=callback)

    assert final.status == WorkflowStatus.COMPLETED
    assert "workflow.started" in events_received
    assert "node.started" in events_received
    assert "node.completed" in events_received
    assert "workflow.completed" in events_received
