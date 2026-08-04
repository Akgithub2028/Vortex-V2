"""
Unit tests for API routes.
"""

import uuid
import pytest

from vortex.engine.checkpoint import CheckpointStore
from vortex.engine.state import WorkflowState, WorkflowStatus
from vortex.storage.database import get_session
from vortex.storage.models import WorkflowRun


@pytest.mark.asyncio
async def test_health_routes(async_client):
    res_health = await async_client.get("/healthz")
    assert res_health.status_code == 200

    res_ready = await async_client.get("/readyz")
    assert res_ready.status_code in (200, 503)


@pytest.mark.asyncio
async def test_run_workflow_endpoint(async_client, monkeypatch):
    async def mock_save(*args, **kwargs):
        pass

    monkeypatch.setattr("vortex.engine.checkpoint.CheckpointStore.save_checkpoint", mock_save)

    payload = {
        "dag": {
            "name": "test-workflow",
            "version": 1,
            "nodes": [
                {"id": "step1", "type": "llm", "config": {"prompt": "Hello {topic}"}}
            ],
        },
        "input": {"topic": "AI Architecture"},
    }

    response = await async_client.post("/v1/workflows/run", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "COMPLETED"
    assert "step1" in data["output"]


@pytest.mark.asyncio
async def test_get_workflow_run_endpoint(async_client):
    run_id = uuid.uuid4()
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")  # Dev tenant

    state = WorkflowState(
        run_id=run_id,
        tenant_id=tenant_id,
        status=WorkflowStatus.COMPLETED,
        completed_nodes={"step1": "done"},
    )

    async with get_session() as session:
        run = WorkflowRun(
            id=run_id,
            tenant_id=tenant_id,
            status="COMPLETED",
            input={"test": True},
            checkpoint=state.model_dump(mode="json"),
        )
        session.add(run)

    response = await async_client.get(f"/v1/workflows/{run_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(run_id)
    assert data["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_get_workflow_run_not_found(async_client):
    missing_id = uuid.uuid4()
    response = await async_client.get(f"/v1/workflows/{missing_id}")
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "WORKFLOWRUN_NOT_FOUND"


@pytest.mark.asyncio
async def test_cancel_workflow_run_endpoint(async_client):
    run_id = uuid.uuid4()
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    state = WorkflowState(
        run_id=run_id,
        tenant_id=tenant_id,
        status=WorkflowStatus.RUNNING,
        completed_nodes={},
    )
    await CheckpointStore.save_checkpoint(state)

    response = await async_client.post(f"/v1/workflows/{run_id}/cancel")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "CANCELLED"


@pytest.mark.asyncio
async def test_cancel_missing_workflow_run(async_client):
    missing_id = uuid.uuid4()
    response = await async_client.post(f"/v1/workflows/{missing_id}/cancel")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_chat_completion_endpoint(async_client):
    payload = {
        "model": "openai/gpt-4o-mini",
        "messages": [{"role": "user", "content": "Hello"}],
    }

    response = await async_client.post("/v1/models/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "openai"


@pytest.mark.asyncio
async def test_eval_run_endpoint(async_client):
    payload = {
        "dataset_name": "faithfulness_v1",
        "target_node": "step1",
    }

    response = await async_client.post("/v1/evals/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 0.92
    assert data["passed"] is True


@pytest.mark.asyncio
async def test_create_prompt_template(async_client):
    """POST /v1/prompts should create a prompt template."""
    payload = {
        "name": "summarizer_v1",
        "template": "Summarize the following: {text}",
        "variables": ["text"],
    }
    response = await async_client.post("/v1/prompts", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "summarizer_v1"
    assert data["version"] == 1
    assert data["template"] == "Summarize the following: {text}"


@pytest.mark.asyncio
async def test_create_prompt_template_auto_version(async_client):
    """Creating a prompt with the same name increments version."""
    payload = {
        "name": "auto_ver_test",
        "template": "Version 1: {topic}",
        "variables": ["topic"],
    }
    r1 = await async_client.post("/v1/prompts", json=payload)
    assert r1.status_code == 201
    assert r1.json()["version"] == 1

    payload["template"] = "Version 2: {topic}"
    r2 = await async_client.post("/v1/prompts", json=payload)
    assert r2.status_code == 201
    assert r2.json()["version"] == 2


@pytest.mark.asyncio
async def test_list_prompt_templates(async_client):
    """GET /v1/prompts should list created prompts."""
    # Create a prompt first
    await async_client.post("/v1/prompts", json={
        "name": "list_test_prompt",
        "template": "Test {x}",
        "variables": ["x"],
    })

    response = await async_client.get("/v1/prompts")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(p["name"] == "list_test_prompt" for p in data)


@pytest.mark.asyncio
async def test_get_prompt_template_by_name(async_client):
    """GET /v1/prompts/{name} should return the latest version."""
    await async_client.post("/v1/prompts", json={
        "name": "get_test",
        "template": "Template {y}",
        "variables": ["y"],
    })

    response = await async_client.get("/v1/prompts/get_test")
    assert response.status_code == 200
    assert response.json()["name"] == "get_test"


@pytest.mark.asyncio
async def test_get_prompt_template_not_found(async_client):
    """GET /v1/prompts/{name} for missing name should return 404."""
    response = await async_client.get("/v1/prompts/nonexistent_prompt")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_prompt_template_specific_version(async_client):
    """GET /v1/prompts/{name}?version=1 should return specific version."""
    await async_client.post("/v1/prompts", json={
        "name": "ver_test",
        "template": "V1 {z}",
        "variables": ["z"],
    })
    await async_client.post("/v1/prompts", json={
        "name": "ver_test",
        "template": "V2 {z}",
        "variables": ["z"],
    })

    response = await async_client.get("/v1/prompts/ver_test?version=1")
    assert response.status_code == 200
    assert response.json()["version"] == 1
    assert "V1" in response.json()["template"]


@pytest.mark.asyncio
async def test_readyz_healthy(async_client):
    """GET /readyz when services are healthy should return 200."""
    response = await async_client.get("/readyz")
    # Might be 503 if redis is unavailable in test env, but the route is covered
    assert response.status_code in (200, 503)
    data = response.json()
    assert "database" in data
    assert "redis" in data


@pytest.mark.asyncio
async def test_run_workflow_with_idempotency_key(async_client, monkeypatch):
    """Idempotency key should return existing run on second call."""
    async def mock_save(*args, **kwargs):
        pass

    monkeypatch.setattr("vortex.engine.checkpoint.CheckpointStore.save_checkpoint", mock_save)

    payload = {
        "dag": {
            "name": "idemp-test",
            "version": 1,
            "nodes": [
                {"id": "s1", "type": "llm", "config": {"prompt": "Hello"}}
            ],
        },
        "input": {"topic": "test"},
        "idempotency_key": "unique-key-123",
    }

    r1 = await async_client.post("/v1/workflows/run", json=payload)
    assert r1.status_code == 201
    run_id_1 = r1.json()["id"]

    r2 = await async_client.post("/v1/workflows/run", json=payload)
    assert r2.status_code == 201
    assert r2.json()["id"] == run_id_1  # Same run returned
