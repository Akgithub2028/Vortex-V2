"""
Extended unit tests for Workflow routes in src/vortex/api/routes/workflows.py.
Coverage boost for workflow execution, streaming, cancel, and HITL approval endpoints.
"""

from __future__ import annotations

import uuid

import pytest

from vortex.engine.state import DAGDefinition, NodeDefinition, WorkflowState, WorkflowStatus


@pytest.mark.asyncio
async def test_workflow_idempotency_hit(async_client):
    dag = {"name": "test-idempotency", "nodes": [{"id": "n1", "type": "tool", "config": {"tool_name": "calculator", "expression": "2+2"}}]}
    req_data = {
        "dag": dag,
        "input": {"x": 10},
        "idempotency_key": f"idem-{uuid.uuid4()}",
    }

    # First Run
    res1 = await async_client.post("/v1/workflows/run", json=req_data)
    assert res1.status_code == 201
    run1 = res1.json()

    # Second Run with same Idempotency Key -> Should hit idempotency branch
    res2 = await async_client.post("/v1/workflows/run", json=req_data)
    assert res2.status_code == 201
    run2 = res2.json()
    assert run1["id"] == run2["id"]


@pytest.mark.asyncio
async def test_workflow_stream_endpoint(async_client):
    dag = {"name": "test-stream", "nodes": [{"id": "n1", "type": "tool", "config": {"tool_name": "calculator", "expression": "5*5"}}]}
    req_data = {"dag": dag, "input": {}}

    res = await async_client.post("/v1/workflows/stream", json=req_data)
    assert res.status_code in (200, 201)


@pytest.mark.asyncio
async def test_get_workflow_run_endpoint(async_client):
    dev_tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    run_id = uuid.uuid4()
    state = WorkflowState(
        run_id=run_id,
        tenant_id=dev_tenant_id,
        status=WorkflowStatus.COMPLETED,
        completed_nodes={"n1": {"result": 42}},
        total_tokens=100,
        total_cost_usd=0.001,
    )
    from vortex.engine.checkpoint import CheckpointStore
    from vortex.storage.database import get_session
    from vortex.storage.models import WorkflowRun

    async with get_session() as session:
        session.add(
            WorkflowRun(
                id=run_id,
                tenant_id=dev_tenant_id,
                status="COMPLETED",
                input={},
                output={"n1": {"result": 42}},
                total_tokens=100,
                total_cost_usd=0.001,
            )
        )

    await CheckpointStore.save_checkpoint(state)

    # Fetch existing run
    res = await async_client.get(f"/v1/workflows/{run_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == str(run_id)
    assert data["status"] == "COMPLETED"

    # Fetch non-existent run -> 404
    res_404 = await async_client.get(f"/v1/workflows/{uuid.uuid4()}")
    assert res_404.status_code == 404


@pytest.mark.asyncio
async def test_cancel_workflow_run_endpoint(async_client):
    dev_tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    run_id = uuid.uuid4()
    state = WorkflowState(
        run_id=run_id,
        tenant_id=dev_tenant_id,
        status=WorkflowStatus.RUNNING,
    )
    from vortex.engine.checkpoint import CheckpointStore
    from vortex.storage.database import get_session
    from vortex.storage.models import WorkflowRun

    async with get_session() as session:
        session.add(
            WorkflowRun(
                id=run_id,
                tenant_id=dev_tenant_id,
                status="RUNNING",
                input={},
            )
        )

    await CheckpointStore.save_checkpoint(state)

    res = await async_client.post(f"/v1/workflows/{run_id}/cancel")
    assert res.status_code == 200
    assert res.json()["status"] == "CANCELLED"


@pytest.mark.asyncio
async def test_approve_human_node_endpoint(async_client):
    dev_tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    run_id = uuid.uuid4()
    dag = DAGDefinition(
        name="test-approve",
        nodes=[
            NodeDefinition(id="h1", type="human", config={"prompt": "Approve"}),
            NodeDefinition(id="t1", type="tool", config={"tool_name": "calculator", "expression": "1+1"}, dependencies=["h1"]),
        ],
    )
    state = WorkflowState(
        run_id=run_id,
        tenant_id=dev_tenant_id,
        status=WorkflowStatus.AWAITING_APPROVAL,
        variables={"_dag": dag.model_dump(mode="json")},
    )
    from vortex.engine.checkpoint import CheckpointStore
    from vortex.storage.database import get_session
    from vortex.storage.models import WorkflowRun

    async with get_session() as session:
        session.add(
            WorkflowRun(
                id=run_id,
                tenant_id=dev_tenant_id,
                status="AWAITING_APPROVAL",
                input={},
            )
        )

    await CheckpointStore.save_checkpoint(state)

    # 1. Reject approval
    res_reject = await async_client.post(
        f"/v1/workflows/{run_id}/nodes/h1/approve",
        json={"approved": False, "feedback": "Rejected in test"},
    )
    assert res_reject.status_code == 200
    assert res_reject.json()["status"] == "FAILED"

    # 2. Reset state to AWAITING_APPROVAL and approve
    state.status = WorkflowStatus.AWAITING_APPROVAL
    await CheckpointStore.save_checkpoint(state)

    res_approve = await async_client.post(
        f"/v1/workflows/{run_id}/nodes/h1/approve",
        json={"approved": True, "feedback": "Approved!"},
    )
    assert res_approve.status_code == 200
    assert res_approve.json()["status"] in ("COMPLETED", "RUNNING")
