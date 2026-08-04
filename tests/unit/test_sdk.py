"""
Unit tests for the Vortex Python SDK (Workflow builder & VortexClient).
"""

import uuid
import pytest
from unittest.mock import AsyncMock, patch

from vortex.sdk.client import VortexClient
from vortex.sdk.types import SDKWorkflowRunResponse
from vortex.sdk.workflow import Workflow


def test_workflow_builder_fluent():
    wf = Workflow(name="sdk-test-workflow")
    wf.add_llm_node("llm1", prompt="Hello {topic}", model="openai/gpt-4o")
    wf.add_tool_node("tool1", tool_name="search", dependencies=["llm1"])
    wf.add_branch_node("branch1", condition_variable="flag", truthy_target="t", falsy_target="f", dependencies=["tool1"])
    wf.add_parallel_node("parallel1", branches=["b1", "b2"])
    wf.add_eval_node("eval1", target_node="llm1", scorer_name="faithfulness", threshold=0.8, dependencies=["llm1"])
    wf.add_human_node("human1", instructions="Approve", dependencies=["eval1"])

    d = wf.to_dict()
    assert d["name"] == "sdk-test-workflow"
    assert len(d["nodes"]) == 6
    assert d["nodes"][0]["type"] == "llm"
    assert d["nodes"][1]["type"] == "tool"
    assert d["nodes"][2]["type"] == "branch"
    assert d["nodes"][3]["type"] == "parallel"
    assert d["nodes"][4]["type"] == "eval"
    assert d["nodes"][5]["type"] == "human"


@pytest.mark.asyncio
async def test_sdk_client_methods(monkeypatch):
    client = VortexClient(base_url="http://localhost:8000", api_key="vx-live-test")
    assert client.headers["Authorization"] == "Bearer vx-live-test"

    wf = Workflow(name="client-test")
    wf.add_llm_node("node1", prompt="Hi")

    run_id = uuid.uuid4()
    mock_run_json = {
        "id": str(run_id),
        "status": "COMPLETED",
        "input": {"topic": "test"},
        "output": {"node1": "response"},
        "total_tokens": 100,
        "total_cost_usd": 0.001,
        "created_at": "2026-08-03T21:45:00Z",
    }

    class DummyResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return mock_run_json

    class DummyAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def post(self, url, **kwargs):
            return DummyResponse()

        async def get(self, url, **kwargs):
            return DummyResponse()

    monkeypatch.setattr(client, "_get_client", lambda: DummyAsyncClient())

    run_res = await client.run_workflow(wf, input={"topic": "test"})
    assert isinstance(run_res, SDKWorkflowRunResponse)
    assert run_res.status == "COMPLETED"

    get_res = await client.get_workflow_run(run_id)
    assert get_res.id == run_id

    cancel_res = await client.cancel_workflow_run(run_id)
    assert cancel_res.status == "COMPLETED"

    approve_res = await client.approve_human_node(run_id, "human1", approved=True)
    assert approve_res.id == run_id

    mock_prompt_json = {
        "id": str(uuid.uuid4()),
        "name": "summary_template",
        "version": 1,
        "template": "Summarize {text}",
        "variables": ["text"],
        "created_at": "2026-08-03T21:45:00Z",
    }

    class DummyPromptResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return mock_prompt_json

    class DummyPromptAsyncClient(DummyAsyncClient):
        async def post(self, url, **kwargs):
            return DummyPromptResponse()

    monkeypatch.setattr(client, "_get_client", lambda: DummyPromptAsyncClient())
    prompt_res = await client.create_prompt_template("summary_template", "Summarize {text}", ["text"])
    assert prompt_res.name == "summary_template"
    assert prompt_res.version == 1
