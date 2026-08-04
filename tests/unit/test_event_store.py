"""
Unit tests for Vortex EventStore component.
"""

import uuid

import pytest

from vortex.engine.event_store import EventStore
from vortex.storage.database import init_db


@pytest.mark.asyncio
async def test_event_store_append_and_sequence():
    await init_db()
    EventStore.clear_cache()

    tenant_id = uuid.uuid4()
    run_id = uuid.uuid4()

    event1 = await EventStore.append_event(
        tenant_id=tenant_id,
        run_id=run_id,
        event_type="WorkflowStarted",
        event_data={"input": {"topic": "AI"}},
    )

    assert event1.sequence_number == 1
    assert event1.event_type == "WorkflowStarted"
    assert event1.run_id == run_id

    event2 = await EventStore.append_event(
        tenant_id=tenant_id,
        run_id=run_id,
        event_type="NodeStarted",
        event_data={"node_id": "llm1"},
    )

    assert event2.sequence_number == 2
    assert event2.event_type == "NodeStarted"

    events = await EventStore.get_events(run_id)
    assert len(events) == 2
    assert events[0].sequence_number == 1
    assert events[1].sequence_number == 2

    stream = EventStore.get_event_stream(run_id)
    assert len(stream) == 2
    assert stream[0]["event_type"] == "WorkflowStarted"
    assert stream[1]["event_type"] == "NodeStarted"
