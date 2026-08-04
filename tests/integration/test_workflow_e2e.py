"""
End-to-end integration tests for Vortex workflow engine, idempotency, cancellation, HITL, and SSE.
"""

import uuid
import pytest

from vortex.engine.state import WorkflowStatus
from vortex.storage.database import get_session
from vortex.storage.models import WorkflowRun


@pytest.mark.integration
@pytest.mark.asyncio
async def test_workflow_e2e_execution(async_client, monkeypatch):
    async def mock_save(*args, **kwargs):
        pass

    monkeypatch.setattr("vortex.engine.checkpoint.CheckpointStore.save_checkpoint", mock_save)

    payload = {
        "dag": {
            "name": "e2e-workflow",
            "version": 1,
            "nodes": [
                {"id": "llm1", "type": "llm", "config": {"prompt": "Analyze {query}"}},
                {"id": "eval1", "type": "eval", "dependencies": ["llm1"], "config": {"scorer": "faithfulness", "threshold": 0.5, "target_node": "llm1"}},
            ],
        },
        "input": {"query": "Distributed Consensus"},
    }

    response = await async_client.post("/v1/workflows/run", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["status"] == "COMPLETED"
    assert "llm1" in data["output"]
    assert "eval1" in data["output"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_workflow_idempotency_key(async_client):
    run_id = uuid.uuid4()
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    idempotency_key = "idemp-key-999"

    # Pre-populate DB with existing run
    async with get_session() as session:
        run = WorkflowRun(
            id=run_id,
            tenant_id=tenant_id,
            status="COMPLETED",
            input={"query": "AI Engine"},
            output={"step1": "cached_result"},
            idempotency_key=idempotency_key,
        )
        session.add(run)

    payload = {
        "dag": {
            "name": "e2e-workflow",
            "version": 1,
            "nodes": [{"id": "step1", "type": "llm", "config": {"prompt": "Hello"}}],
        },
        "input": {"query": "AI Engine"},
        "idempotency_key": idempotency_key,
    }

    response = await async_client.post("/v1/workflows/run", json=payload)
    assert response.status_code == 201
    data = response.json()

    # Reused existing run
    assert data["id"] == str(run_id)
    assert data["output"]["step1"] == "cached_result"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_workflow_cancellation(async_client):
    run_id = uuid.uuid4()
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    # Insert active run in DB
    async with get_session() as session:
        run = WorkflowRun(
            id=run_id,
            tenant_id=tenant_id,
            status="RUNNING",
            input={"test": True},
            checkpoint={"run_id": str(run_id), "tenant_id": str(tenant_id), "status": "RUNNING"},
        )
        session.add(run)

    response = await async_client.post(f"/v1/workflows/{run_id}/cancel")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "CANCELLED"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_hitl_approval_flow(async_client):
    # 1. Run workflow with Human node
    payload = {
        "dag": {
            "name": "hitl-workflow",
            "version": 1,
            "nodes": [
                {"id": "human1", "type": "human", "config": {"prompt": "Approve deploy?"}},
                {"id": "deploy", "type": "tool", "dependencies": ["human1"], "config": {"tool_name": "deploy"}},
            ],
        },
        "input": {"target": "production"},
    }

    resp1 = await async_client.post("/v1/workflows/run", json=payload)
    assert resp1.status_code == 201
    data1 = resp1.json()
    run_id = data1["id"]
    assert data1["status"] == "AWAITING_APPROVAL"

    # 2. Submit approval directly
    resp2 = await async_client.post(
        f"/v1/workflows/{run_id}/nodes/human1/approve",
        json={"approved": True, "feedback": "Approved by Ops"},
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["status"] == "COMPLETED"
    assert "deploy" in data2["output"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_sse_streaming_workflow(async_client, monkeypatch):
    async def mock_save(*args, **kwargs):
        pass

    monkeypatch.setattr("vortex.engine.checkpoint.CheckpointStore.save_checkpoint", mock_save)

    payload = {
        "dag": {
            "name": "stream-workflow",
            "version": 1,
            "nodes": [{"id": "step1", "type": "llm", "config": {"prompt": "Stream test"}}],
        },
        "input": {},
    }

    response = await async_client.post("/v1/workflows/stream", json=payload)
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    assert "workflow.started" in response.text
    assert "workflow.finished" in response.text


@pytest.mark.integration
@pytest.mark.asyncio
async def test_hitl_rejection_and_error_cases(async_client):
    # 1. Run workflow with Human node
    payload = {
        "dag": {
            "name": "hitl-reject-workflow",
            "version": 1,
            "nodes": [{"id": "human1", "type": "human", "config": {"prompt": "Approve deploy?"}}],
        },
        "input": {},
    }

    resp1 = await async_client.post("/v1/workflows/run", json=payload)
    data1 = resp1.json()
    run_id = data1["id"]

    # Test invalid approval call when already approved or invalid status
    resp_invalid = await async_client.post(f"/v1/workflows/{uuid.uuid4()}/nodes/human1/approve", json={"approved": True})
    assert resp_invalid.status_code == 404

    # Submit rejection
    resp2 = await async_client.post(
        f"/v1/workflows/{run_id}/nodes/human1/approve",
        json={"approved": False, "feedback": "Rejected by SecOps"},
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["status"] == "FAILED"

    # Test approval call on already completed/failed workflow
    resp_reapprove = await async_client.post(
        f"/v1/workflows/{run_id}/nodes/human1/approve",
        json={"approved": True},
    )
    assert resp_reapprove.status_code == 422
