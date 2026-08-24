"""
Unit tests for ToolRegistry, Built-in Tools, ToolNode integration, and Structured Outputs.
"""

from __future__ import annotations

import uuid
import pytest

from vortex.engine.nodes import create_node
from vortex.engine.nodes.llm_node import LLMNode
from vortex.engine.state import NodeDefinition, WorkflowState
from vortex.engine.tools import ToolRegistry, tool_registry
from vortex.gateway.providers.base import CompletionRequest

TEST_RUN_ID = uuid.uuid4()
TEST_TENANT_ID = uuid.uuid4()


@pytest.mark.asyncio
async def test_tool_registry_text_processor():
    result = await tool_registry.execute_tool("text_processor", {"text": "hello vortex", "action": "uppercase"})
    assert result["processed_text"] == "HELLO VORTEX"
    assert result["action"] == "uppercase"


@pytest.mark.asyncio
async def test_tool_registry_json_extractor():
    payload = '{"status": "ok", "user": {"name": "Alice"}}'
    result = await tool_registry.execute_tool("json_extractor", {"json_string": payload, "key": "user"})
    assert result["extracted_data"] == {"name": "Alice"}
    assert result["success"] is True


@pytest.mark.asyncio
async def test_tool_registry_web_search_stub():
    result = await tool_registry.execute_tool("web_search_stub", {"query": "AI Agents", "limit": 2})
    assert result["query"] == "AI Agents"
    assert len(result["results"]) == 2
    assert "Overview of AI Agents" in result["results"][0]["title"]


@pytest.mark.asyncio
async def test_tool_node_execution_with_registry():
    node_def = NodeDefinition(
        id="tool1",
        type="tool",
        config={
            "tool_name": "text_processor",
            "arguments": {"text": "$input_text", "action": "reverse"},
        },
    )
    node = create_node(node_def)
    state = WorkflowState(
        run_id=TEST_RUN_ID,
        tenant_id=TEST_TENANT_ID,
        variables={"input_text": "VORTEX"},
    )

    output = await node.execute(state)

    assert output["status"] == "success"
    assert output["tool"] == "text_processor"
    assert output["result"] == "XETROV"


@pytest.mark.asyncio
async def test_llm_node_structured_output_schema():
    schema = {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "sentiment": {"type": "string"},
        },
        "required": ["summary", "sentiment"],
    }
    node_def = NodeDefinition(
        id="llm1",
        type="llm",
        config={
            "prompt": "Analyze {text}",
            "model": "openai/gpt-4o-mini",
            "output_schema": schema,
        },
    )
    node = create_node(node_def)
    state = WorkflowState(
        run_id=TEST_RUN_ID,
        tenant_id=TEST_TENANT_ID,
        variables={"text": "Vortex launch was successful."},
    )

    output = await node.execute(state)

    assert "text" in output
    assert output["provider"] == "openai"
