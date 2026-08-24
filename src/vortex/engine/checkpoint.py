"""
Vortex Checkpoint Store — PostgreSQL/SQLite-backed state persistence, in-memory caching, and crash recovery.

Implements:
- Checkpoint serialization and storage
- In-memory cache for ultra-fast run state lookup
- Crash recovery: detects orphaned RUNNING workflows with stale heartbeats and resumes them
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta, timezone
from typing import ClassVar

from sqlalchemy import select

from vortex.config import get_settings
from vortex.engine.state import WorkflowState, WorkflowStatus
from vortex.observability.logger import get_logger
from vortex.storage.database import get_session
from vortex.storage.models import WorkflowRun

logger = get_logger(__name__)


class CheckpointStore:
    """Handles workflow state checkpointing and recovery in PostgreSQL/SQLite and memory."""

    _cache: ClassVar[dict[str, WorkflowState]] = {}

    @classmethod
    async def save_checkpoint(cls, state: WorkflowState) -> None:
        """
        Persist current WorkflowState to database JSON column and in-memory cache.

        Updates or creates `WorkflowRun` record.
        """
        state.version += 1
        state.updated_at = datetime.now(UTC)
        key = str(state.run_id)
        cls._cache[key] = state.model_copy(deep=True)

        output_vars = {k: v for k, v in state.completed_nodes.items() if not k.startswith("_")}
        try:
            async with get_session() as session:
                run = await session.get(WorkflowRun, state.run_id)
                if not run:
                    stmt = select(WorkflowRun).where(WorkflowRun.id == state.run_id)
                    res = await session.execute(stmt)
                    run = res.scalar_one_or_none()

                if run:
                    run.checkpoint = state.model_dump(mode="json")
                    run.status = state.status.value
                    run.output = output_vars
                    run.total_tokens = state.total_tokens
                    run.total_cost_usd = state.total_cost_usd
                    run.heartbeat_at = datetime.now(UTC)
                    if state.is_terminal():
                        run.completed_at = datetime.now(UTC)
                    session.add(run)
                else:
                    run = WorkflowRun(
                        id=state.run_id,
                        tenant_id=state.tenant_id,
                        status=state.status.value,
                        input=state.variables,
                        output=output_vars,
                        checkpoint=state.model_dump(mode="json"),
                        total_tokens=state.total_tokens,
                        total_cost_usd=state.total_cost_usd,
                        heartbeat_at=datetime.now(UTC),
                    )
                    session.add(run)
        except Exception as e:
            logger.warning("DB checkpoint update degraded to in-memory cache", run_id=key, error=str(e))
            raise e

        logger.debug(
            "Saved checkpoint",
            run_id=key,
            version=state.version,
            status=state.status.value,
        )

    @classmethod
    async def load_checkpoint(cls, run_id: uuid.UUID | str) -> WorkflowState | None:
        """Load WorkflowState from cache or database for a given run_id."""
        key = str(run_id)
        uid = uuid.UUID(key) if isinstance(run_id, str) else run_id

        if key in cls._cache:
            return cls._cache[key].model_copy(deep=True)

        try:
            async with get_session() as session:
                from vortex.engine.event_store import EventStore
                from vortex.engine.projector import StateProjector

                events = await EventStore.get_events(uid, session=session)
                if events:
                    state = StateProjector.project(events)
                    cls._cache[key] = state.model_copy(deep=True)
                    return state

                run = await session.get(WorkflowRun, uid)
                if not run:
                    stmt = select(WorkflowRun).where(WorkflowRun.id == uid)
                    res = await session.execute(stmt)
                    run = res.scalar_one_or_none()

                if not run or not run.checkpoint:
                    return None

                state = WorkflowState.model_validate(run.checkpoint)
                cls._cache[key] = state.model_copy(deep=True)
                return state
        except Exception as e:
            logger.error("Failed to load checkpoint from DB", run_id=key, error=str(e))
            return None

    @classmethod
    async def update_heartbeat(cls, run_id: uuid.UUID | str) -> None:
        """Update the heartbeat timestamp for an active workflow run."""
        key = str(run_id)
        uid = uuid.UUID(key) if isinstance(run_id, str) else run_id

        if key in cls._cache:
            cls._cache[key].updated_at = datetime.now(UTC)

        try:
            async with get_session() as session:
                run = await session.get(WorkflowRun, uid)
                if run:
                    run.heartbeat_at = datetime.now(UTC)
        except Exception as e:
            logger.warning("Heartbeat update failed", run_id=key, error=str(e))

    @classmethod
    async def recover_orphaned_workflows(cls) -> list[tuple[uuid.UUID, uuid.UUID]]:
        """
        Detect and recover orphaned workflows.

        Finds all workflow runs with status='RUNNING' whose heartbeat is older
        than `engine_orphan_timeout_seconds`. Returns list of (run_id, tenant_id) tuples.
        """
        settings = get_settings()
        cutoff = datetime.now(UTC) - timedelta(seconds=settings.engine_orphan_timeout_seconds)

        recovered: list[tuple[uuid.UUID, uuid.UUID]] = []

        try:
            async with get_session() as session:
                stmt = select(WorkflowRun).where(
                    WorkflowRun.status == WorkflowStatus.RUNNING.value,
                    WorkflowRun.heartbeat_at < cutoff,
                )
                result = await session.execute(stmt)
                orphaned_runs = result.scalars().all()

                for run in orphaned_runs:
                    logger.warning(
                        "Detected orphaned workflow run",
                        run_id=str(run.id),
                        last_heartbeat=run.heartbeat_at.isoformat() if run.heartbeat_at else "none",
                    )
                    uid = run.id if isinstance(run.id, uuid.UUID) else uuid.UUID(str(run.id))
                    tid = run.tenant_id if isinstance(run.tenant_id, uuid.UUID) else uuid.UUID(str(run.tenant_id))
                    recovered.append((uid, tid))
        except Exception as e:
            logger.error("Error during orphan recovery search", error=str(e))

        return recovered
