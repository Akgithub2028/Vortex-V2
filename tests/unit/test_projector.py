"""
Unit tests for Vortex StateProjector CQRS component.
"""

import uuid
from datetime import datetime
from decimal import Decimal

import pytest

from vortex.engine.projector import StateProjector
from vortex.engine.state import WorkflowStatus
from vortex.storage.database import get_session, init_db
from vortex.storage.models import WorkflowEvent


@pytest.mark.asyncio
async def test_state_projector_reduction():
    tenant_id = uuid.uuid4()
    run_id = uuid.uuid4()

    events = [
        WorkflowEvent(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            run_id=run_id,
            sequence_number=1,
            event_type="WorkflowStarted",
            event_data={"input": {"topic": "Quantum Computing"}},
            timestamp=datetime.utcnow(),
        ),
        WorkflowEvent(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            run_id=run_id,
            sequence_number=2,
            event_type="NodeStarted",
            event_data={"node_id": "llm1", "node_type": "llm"},
            timestamp=datetime.utcnow(),
        ),
        WorkflowEvent(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            run_id=run_id,
            sequence_number=3,
            event_type="NodeCompleted",
            event_data={"node_id": "llm1", "output": {"text": "Summary of quantum"}, "tokens": 150, "cost_usd": "0.003"},
            timestamp=datetime.utcnow(),
        ),
        WorkflowEvent(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            run_id=run_id,
            sequence_number=4,
            event_type="WorkflowCompleted",
            event_data={"output": {"text": "Summary of quantum"}},
            timestamp=datetime.utcnow(),
        ),
    ]

    state = StateProjector.project(events)

    assert state.run_id == run_id
    assert state.tenant_id == tenant_id
    assert state.status == WorkflowStatus.COMPLETED
    assert state.total_tokens == 150
    assert state.total_cost_usd == Decimal("0.003")
    assert "llm1" in state.completed_nodes
    assert state.variables["_output"] == {"text": "Summary of quantum"}


@pytest.mark.asyncio
async def test_state_projector_read_model_materialization():
    await init_db()
    tenant_id = uuid.uuid4()
    run_id = uuid.uuid4()

    events = [
        WorkflowEvent(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            run_id=run_id,
            sequence_number=1,
            event_type="WorkflowStarted",
            event_data={"input": {"prompt": "Hello world"}},
            timestamp=datetime.utcnow(),
        ),
        WorkflowEvent(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            run_id=run_id,
            sequence_number=2,
            event_type="NodeCompleted",
            event_data={"node_id": "step1", "node_type": "tool", "output": {"res": "ok"}, "tokens": 50, "cost_usd": "0.001"},
            timestamp=datetime.utcnow(),
        ),
        WorkflowEvent(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            run_id=run_id,
            sequence_number=3,
            event_type="WorkflowCompleted",
            event_data={"output": {"res": "ok"}},
            timestamp=datetime.utcnow(),
        ),
    ]

    async with get_session() as session:
        run = await StateProjector.materialize_read_model(session, run_id, events)
        assert run.id == run_id
        assert run.status == "COMPLETED"
        assert run.total_tokens == 50
        assert run.total_cost_usd == Decimal("0.001")


@pytest.mark.asyncio
async def test_state_projector_human_and_failure_events():
    tenant_id = uuid.uuid4()
    run_id = uuid.uuid4()

    events = [
        WorkflowEvent(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            run_id=run_id,
            sequence_number=1,
            event_type="WorkflowStarted",
            event_data={"input": {}},
            timestamp=datetime.utcnow(),
        ),
        WorkflowEvent(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            run_id=run_id,
            sequence_number=2,
            event_type="NodeStarted",
            event_data={"node_id": "h1"},
            timestamp=datetime.utcnow(),
        ),
        WorkflowEvent(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            run_id=run_id,
            sequence_number=3,
            event_type="HumanApprovalRequested",
            event_data={"node_id": "h1"},
            timestamp=datetime.utcnow(),
        ),
        WorkflowEvent(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            run_id=run_id,
            sequence_number=4,
            event_type="HumanApproved",
            event_data={"node_id": "h1", "output": {"approved": True}},
            timestamp=datetime.utcnow(),
        ),
        WorkflowEvent(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            run_id=run_id,
            sequence_number=5,
            event_type="NodeFailed",
            event_data={"node_id": "n2", "error": "API Error"},
            timestamp=datetime.utcnow(),
        ),
        WorkflowEvent(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            run_id=run_id,
            sequence_number=6,
            event_type="WorkflowFailed",
            event_data={"error": "API Error"},
            timestamp=datetime.utcnow(),
        ),
    ]

    state = StateProjector.project(events)
    assert state.status == WorkflowStatus.FAILED
    assert "h1" in state.completed_nodes
    assert state.failed_nodes["n2"] == "API Error"
    assert state.variables["_workflow_error"] == "API Error"
