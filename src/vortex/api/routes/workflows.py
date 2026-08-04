"""
API routes for Workflow execution, streaming, cancellation, and HITL approval.

POST /v1/workflows/run — Submit and execute a workflow (with idempotency support)
POST /v1/workflows/stream — Submit and execute a workflow with real-time SSE event streaming
GET /v1/workflows/{run_id} — Get workflow run status and outputs
POST /v1/workflows/{run_id}/cancel — Cancel an active workflow run
POST /v1/workflows/{run_id}/nodes/{node_id}/approve — Approve a paused HITL human node
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sse_starlette.sse import EventSourceResponse

from vortex.api.deps import AuthContext, get_current_auth, require_role
from vortex.api.errors import NotFoundError, ValidationError
from vortex.engine.checkpoint import CheckpointStore
from vortex.engine.executor import DAGExecutor
from vortex.engine.state import DAGDefinition, WorkflowState, WorkflowStatus
from vortex.observability.logger import get_logger
from vortex.storage.database import get_session
from vortex.storage.models import WorkflowRun

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/workflows", tags=["Workflows"])


class RunWorkflowRequest(BaseModel):
    dag: DAGDefinition
    input: dict[str, Any] = Field(default_factory=dict)
    max_cost_usd: float | None = None
    idempotency_key: str | None = None


class WorkflowRunResponse(BaseModel):
    id: uuid.UUID
    status: str
    input: dict[str, Any]
    output: dict[str, Any] | None
    total_tokens: int
    total_cost_usd: float
    created_at: str


class ApproveNodeRequest(BaseModel):
    approved: bool = True
    feedback: str | None = None


@router.post(
    "/run",
    response_model=WorkflowRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit and execute a workflow",
)
async def run_workflow(
    body: RunWorkflowRequest,
    auth: AuthContext = Depends(require_role("member")),
) -> WorkflowRunResponse:
    # 1. Check Idempotency Key
    if body.idempotency_key:
        async with get_session() as session:
            stmt = select(WorkflowRun).where(
                WorkflowRun.tenant_id == auth.tenant_id,
                WorkflowRun.idempotency_key == body.idempotency_key,
            )
            result = await session.execute(stmt)
            existing_run = result.scalar_one_or_none()

            if existing_run:
                logger.info(
                    "Reusing existing workflow run (idempotency key hit)",
                    run_id=str(existing_run.id),
                    key=body.idempotency_key,
                )
                return WorkflowRunResponse(
                    id=existing_run.id,
                    status=existing_run.status,
                    input=existing_run.input,
                    output=existing_run.output,
                    total_tokens=existing_run.total_tokens,
                    total_cost_usd=float(existing_run.total_cost_usd),
                    created_at=existing_run.created_at.isoformat(),
                )

    run_id = uuid.uuid4()
    logger.info("Submitting workflow run request", run_id=str(run_id), tenant=auth.tenant_name)

    # Store DAG in state variables for worker/resume compatibility
    variables = dict(body.input)
    variables["_dag"] = body.dag.model_dump(mode="json")

    state = WorkflowState(
        run_id=run_id,
        tenant_id=auth.tenant_id,
        variables=variables,
        status=WorkflowStatus.PENDING,
    )

    # Initial run record in DB
    async with get_session() as session:
        run_record = WorkflowRun(
            id=run_id,
            tenant_id=auth.tenant_id,
            status=WorkflowStatus.PENDING.value,
            input=body.input,
            checkpoint=state.model_dump(mode="json"),
            idempotency_key=body.idempotency_key,
        )
        session.add(run_record)

    # Execute DAG
    executor = DAGExecutor(body.dag, state)
    final_state = await executor.run()

    # Persist final state checkpoint
    await CheckpointStore.save_checkpoint(final_state)

    # Clean internal _dag variable before returning output
    output_vars = {k: v for k, v in final_state.completed_nodes.items() if not k.startswith("_")}

    return WorkflowRunResponse(
        id=final_state.run_id,
        status=final_state.status.value,
        input=body.input,
        output=output_vars,
        total_tokens=final_state.total_tokens,
        total_cost_usd=float(final_state.total_cost_usd),
        created_at=final_state.updated_at.isoformat(),
    )


@router.post(
    "/stream",
    summary="Execute a workflow with real-time SSE event streaming",
)
async def stream_workflow(
    body: RunWorkflowRequest,
    req: Request,
    auth: AuthContext = Depends(require_role("member")),
) -> EventSourceResponse:
    run_id = uuid.uuid4()
    logger.info("Submitting streaming workflow run", run_id=str(run_id))

    event_queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()

    def callback(event_type: str, payload: dict[str, Any]) -> None:
        event_queue.put_nowait((event_type, payload))

    variables = dict(body.input)
    variables["_dag"] = body.dag.model_dump(mode="json")

    state = WorkflowState(
        run_id=run_id,
        tenant_id=auth.tenant_id,
        variables=variables,
        status=WorkflowStatus.PENDING,
    )

    async def event_generator() -> AsyncGenerator[dict[str, Any], None]:
        executor = DAGExecutor(body.dag, state)
        execution_task = asyncio.create_task(executor.run(event_callback=callback))

        while not execution_task.done() or not event_queue.empty():
            if await req.is_disconnected():
                logger.warning("Client disconnected from SSE stream", run_id=str(run_id))
                break

            try:
                event_type, payload = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                yield {
                    "event": event_type,
                    "data": json.dumps(payload),
                }
            except TimeoutError:
                continue

        final_state = await execution_task
        yield {
            "event": "workflow.finished",
            "data": json.dumps(
                {
                    "run_id": str(final_state.run_id),
                    "status": final_state.status.value,
                    "completed_nodes": list(final_state.completed_nodes.keys()),
                }
            ),
        }

    return EventSourceResponse(event_generator())


@router.get(
    "/{run_id}",
    response_model=WorkflowRunResponse,
    summary="Get workflow run details",
)
async def get_workflow_run(
    run_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_auth),
) -> WorkflowRunResponse:
    state = await CheckpointStore.load_checkpoint(run_id)
    if not state or state.tenant_id != auth.tenant_id:
        raise NotFoundError("WorkflowRun", str(run_id))

    output_vars = {k: v for k, v in state.completed_nodes.items() if not k.startswith("_")}

    return WorkflowRunResponse(
        id=state.run_id,
        status=state.status.value,
        input=state.variables,
        output=output_vars,
        total_tokens=state.total_tokens,
        total_cost_usd=float(state.total_cost_usd),
        created_at=state.updated_at.isoformat(),
    )


@router.post(
    "/{run_id}/cancel",
    response_model=WorkflowRunResponse,
    summary="Cancel an active workflow run",
)
async def cancel_workflow_run(
    run_id: uuid.UUID,
    auth: AuthContext = Depends(require_role("member")),
) -> WorkflowRunResponse:
    state = await CheckpointStore.load_checkpoint(run_id)
    if not state or state.tenant_id != auth.tenant_id:
        raise NotFoundError("WorkflowRun", str(run_id))

    state.status = WorkflowStatus.CANCELLED
    await CheckpointStore.save_checkpoint(state)

    logger.info("Workflow run cancelled by user", run_id=str(run_id))

    return WorkflowRunResponse(
        id=state.run_id,
        status=state.status.value,
        input=state.variables,
        output=state.completed_nodes,
        total_tokens=state.total_tokens,
        total_cost_usd=float(state.total_cost_usd),
        created_at=state.updated_at.isoformat(),
    )


@router.post(
    "/{run_id}/nodes/{node_id}/approve",
    response_model=WorkflowRunResponse,
    summary="Approve a paused HITL human node and resume workflow",
)
async def approve_human_node(
    run_id: uuid.UUID,
    node_id: str,
    body: ApproveNodeRequest,
    auth: AuthContext = Depends(require_role("member")),
) -> WorkflowRunResponse:
    state = await CheckpointStore.load_checkpoint(run_id)
    if not state or state.tenant_id != auth.tenant_id:
        raise NotFoundError("WorkflowRun", str(run_id))

    if state.status != WorkflowStatus.AWAITING_APPROVAL:
        raise ValidationError(f"Workflow '{run_id}' is not awaiting approval (current status: {state.status.value}).")

    # Record approval feedback
    state.completed_nodes[node_id] = {
        "approved": body.approved,
        "feedback": body.feedback,
        "status": "approved" if body.approved else "rejected",
    }
    state.variables[f"{node_id}_approved"] = body.approved

    if not body.approved:
        state.mark_failed(f"Human node '{node_id}' was rejected by reviewer.")
        await CheckpointStore.save_checkpoint(state)
    else:
        # Resume DAG execution
        dag_dict = state.variables.get("_dag")
        if not dag_dict:
            raise ValidationError("Cannot resume workflow: DAG definition missing from checkpoint.")

        dag = DAGDefinition.model_validate(dag_dict)
        executor = DAGExecutor(dag, state)
        state = await executor.run()

    return WorkflowRunResponse(
        id=state.run_id,
        status=state.status.value,
        input=state.variables,
        output=state.completed_nodes,
        total_tokens=state.total_tokens,
        total_cost_usd=float(state.total_cost_usd),
        created_at=state.updated_at.isoformat(),
    )
