"""
Unit tests for Vortex engine DAG nodes.
"""

import uuid

import pytest

from vortex.engine.nodes import create_node
from vortex.engine.nodes.branch_node import BranchNode
from vortex.engine.nodes.eval_node import EvalNode
from vortex.engine.nodes.human_node import HumanNode
from vortex.engine.nodes.llm_node import LLMNode
from vortex.engine.nodes.parallel_node import ParallelNode
from vortex.engine.nodes.tool_node import ToolNode
from vortex.engine.state import NodeDefinition, WorkflowState, WorkflowStatus


@pytest.mark.asyncio
async def test_llm_node_execution():
    node_def = NodeDefinition(id="llm1", type="llm", config={"prompt": "Hello {name}", "model": "openai/gpt-4o-mini"})
    node = create_node(node_def)
    assert isinstance(node, LLMNode)

    state = WorkflowState(run_id=uuid.uuid4(), tenant_id=uuid.uuid4(), variables={"name": "Vortex"})
    output = await node.execute(state)

    assert "Vortex" in output["text"]
    assert output["tokens_in"] > 0
    assert state.total_tokens > 0


@pytest.mark.asyncio
async def test_tool_node_execution():
    node_def = NodeDefinition(
        id="tool1",
        type="tool",
        config={"tool_name": "search", "arguments": {"query": "$q_var", "limit": 5}},
    )
    node = create_node(node_def)
    assert isinstance(node, ToolNode)

    state = WorkflowState(run_id=uuid.uuid4(), tenant_id=uuid.uuid4(), variables={"q_var": "Python AI"})
    output = await node.execute(state)

    assert output["status"] == "success"
    assert output["tool"] == "search"


@pytest.mark.asyncio
async def test_branch_node_execution():
    node_def = NodeDefinition(
        id="branch1",
        type="branch",
        config={"condition_var": "is_valid", "expected_value": True, "true_node": "node_a", "false_node": "node_b"},
    )
    node = create_node(node_def)
    assert isinstance(node, BranchNode)

    # True branch case
    state_true = WorkflowState(run_id=uuid.uuid4(), tenant_id=uuid.uuid4(), variables={"is_valid": True})
    out_true = await node.execute(state_true)
    assert out_true["condition_met"] is True
    assert out_true["selected_branch"] == "node_a"

    # False branch case
    state_false = WorkflowState(run_id=uuid.uuid4(), tenant_id=uuid.uuid4(), variables={"is_valid": False})
    out_false = await node.execute(state_false)
    assert out_false["condition_met"] is False
    assert out_false["selected_branch"] == "node_b"


@pytest.mark.asyncio
async def test_parallel_node_execution():
    node_def = NodeDefinition(id="p1", type="parallel", config={"branches": ["b1", "b2"]})
    node = create_node(node_def)
    assert isinstance(node, ParallelNode)

    state = WorkflowState(run_id=uuid.uuid4(), tenant_id=uuid.uuid4())
    output = await node.execute(state)
    assert output["branches"] == ["b1", "b2"]


@pytest.mark.asyncio
async def test_eval_node_execution():
    node_def = NodeDefinition(
        id="eval1",
        type="eval",
        config={"scorer": "faithfulness", "threshold": 0.7, "target_node": "n1"},
    )
    node = create_node(node_def)
    assert isinstance(node, EvalNode)

    state = WorkflowState(
        run_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        completed_nodes={"n1": {"text": "This is a detailed output from node 1"}},
    )
    output = await node.execute(state)
    assert output["scorer"] == "faithfulness"
    assert output["score"] >= 0.0
    assert isinstance(output["passed"], bool)


@pytest.mark.asyncio
async def test_human_node_execution():
    node_def = NodeDefinition(id="h1", type="human", config={"prompt": "Approve action"})
    node = create_node(node_def)
    assert isinstance(node, HumanNode)

    state = WorkflowState(run_id=uuid.uuid4(), tenant_id=uuid.uuid4())
    output = await node.execute(state)
    assert output["status"] == "awaiting_approval"
    assert state.status == WorkflowStatus.AWAITING_APPROVAL
