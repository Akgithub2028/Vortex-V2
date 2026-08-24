"""
Vortex EventStore — Append-only Event Sourcing database persistence and stream store.

Provides high-performance immutable event logging for workflows:
- Append-only event store (`workflow_events` table)
- Monotonic sequence numbering per run_id
- In-memory event stream caching for sub-millisecond playback
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timezone
from typing import TYPE_CHECKING, Any, ClassVar

from sqlalchemy import func, select

from vortex.observability.logger import get_logger
from vortex.storage.database import get_session
from vortex.storage.models import WorkflowEvent

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class EventStore:
    """Append-only store for workflow execution events."""

    _stream_cache: ClassVar[dict[str, list[dict[str, Any]]]] = {}
    _lock: ClassVar[asyncio.Lock] = asyncio.Lock()

    @classmethod
    async def append_event(
        cls,
        tenant_id: uuid.UUID | str,
        run_id: uuid.UUID | str,
        event_type: str,
        event_data: dict[str, Any],
        session: AsyncSession | None = None,
    ) -> WorkflowEvent:
        """
        Atomically append an event to the workflow_events table with auto-incrementing sequence_number.

        Also updates the in-memory stream cache.
        """
        tid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
        rid = uuid.UUID(str(run_id)) if isinstance(run_id, str) else run_id
        key = str(rid)

        async with cls._lock:
            # Calculate next sequence number for this run_id
            if session is not None:
                event = await cls._persist_event(session, tid, rid, event_type, event_data)
            else:
                async with get_session() as new_session:
                    event = await cls._persist_event(new_session, tid, rid, event_type, event_data)

            # Update stream cache
            event_dict = {
                "id": str(event.id),
                "tenant_id": str(event.tenant_id),
                "run_id": str(event.run_id),
                "sequence_number": event.sequence_number,
                "event_type": event.event_type,
                "event_data": event.event_data,
                "timestamp": event.timestamp.isoformat() if isinstance(event.timestamp, datetime) else str(event.timestamp),
            }
            if key not in cls._stream_cache:
                cls._stream_cache[key] = []
            cls._stream_cache[key].append(event_dict)

            logger.debug(
                "Appended workflow event",
                run_id=key,
                seq=event.sequence_number,
                event_type=event_type,
            )
            return event

    @classmethod
    async def _persist_event(
        cls,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        run_id: uuid.UUID,
        event_type: str,
        event_data: dict[str, Any],
    ) -> WorkflowEvent:
        """Internal helper to calculate max sequence and insert event record."""
        stmt = select(func.coalesce(func.max(WorkflowEvent.sequence_number), 0)).where(WorkflowEvent.run_id == run_id)
        res = await session.execute(stmt)
        max_seq = res.scalar() or 0
        next_seq = max_seq + 1

        event = WorkflowEvent(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            run_id=run_id,
            sequence_number=next_seq,
            event_type=event_type,
            event_data=event_data,
            timestamp=datetime.now(UTC),
        )
        session.add(event)
        await session.flush()
        return event

    @classmethod
    async def get_events(
        cls,
        run_id: uuid.UUID | str,
        min_sequence: int = 0,
        session: AsyncSession | None = None,
    ) -> list[WorkflowEvent]:
        """Fetch all events for a given run_id ordered by sequence_number."""
        rid = uuid.UUID(str(run_id)) if isinstance(run_id, str) else run_id

        if session is not None:
            return await cls._fetch_events(session, rid, min_sequence)

        async with get_session() as new_session:
            return await cls._fetch_events(new_session, rid, min_sequence)

    @classmethod
    async def _fetch_events(
        cls,
        session: AsyncSession,
        run_id: uuid.UUID,
        min_sequence: int,
    ) -> list[WorkflowEvent]:
        stmt = (
            select(WorkflowEvent)
            .where(
                WorkflowEvent.run_id == run_id,
                WorkflowEvent.sequence_number >= min_sequence,
            )
            .order_by(WorkflowEvent.sequence_number.asc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    def get_event_stream(cls, run_id: uuid.UUID | str) -> list[dict[str, Any]]:
        """Retrieve in-memory cached event stream for a run_id."""
        key = str(run_id)
        return cls._stream_cache.get(key, [])

    @classmethod
    def clear_cache(cls) -> None:
        """Clear in-memory stream cache (useful in test tearDown)."""
        cls._stream_cache.clear()
