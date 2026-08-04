"""
Vortex Background Worker & Dead Letter Queue (DLQ) Consumer.

Listens to Redis Stream `vortex:tasks:queue`, processes workflow execution tasks,
applies retry logic with exponential backoff, and routes exhausted tasks to `vortex:tasks:dlq`.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Optional
import uuid

from vortex.config import get_settings
from vortex.engine.checkpoint import CheckpointStore
from vortex.engine.executor import DAGExecutor
from vortex.engine.scheduler import TaskScheduler
from vortex.engine.state import DAGDefinition, WorkflowState, WorkflowStatus
from vortex.observability.logger import get_logger
from vortex.observability.metrics import DLQ_SIZE, WORKFLOW_ACTIVE_RUNS, WORKFLOW_RUNS_TOTAL

logger = get_logger(__name__)


class WorkflowWorker:
    """Background worker processing queued workflows from Redis Stream."""

    def __init__(self, consumer_group: str = "vortex-workers", consumer_name: str = "worker-1"):
        self.consumer_group = consumer_group
        self.consumer_name = consumer_name
        self.running = False

    async def process_task(self, task_data: dict[str, Any]) -> bool:
        """
        Process a single workflow task.

        Returns True if task succeeded, False if failed.
        """
        run_id_str = task_data.get("run_id")
        if not run_id_str:
            logger.error("Task payload missing run_id", task_data=task_data)
            return False

        run_id = uuid.UUID(run_id_str)
        from vortex.storage.lease import LeaseManager

        # Acquire strict TTL lease before processing task
        acquired = await LeaseManager.acquire_lease(run_id_str, self.consumer_name, ttl_seconds=15.0)
        if not acquired:
            logger.info("Worker skipped execution, lease held by another worker", run_id=run_id_str, worker=self.consumer_name)
            return True

        logger.info("Worker starting task execution", run_id=str(run_id))
        WORKFLOW_ACTIVE_RUNS.inc()

        try:
            state = await CheckpointStore.load_checkpoint(run_id)
            if not state:
                logger.error("Checkpoint not found for run_id", run_id=str(run_id))
                return False

            if state.is_terminal():
                logger.info("Workflow already in terminal state", run_id=str(run_id), status=state.status.value)
                return True

            # Reconstruct DAG definition from state variables or DB
            dag_dict = state.variables.get("_dag")
            if not dag_dict:
                logger.error("Missing DAG definition in state variables", run_id=str(run_id))
                return False

            dag = DAGDefinition.model_validate(dag_dict)
            executor = DAGExecutor(dag, state)
            final_state = await executor.run()

            WORKFLOW_RUNS_TOTAL.labels(status=final_state.status.value.lower()).inc()
            logger.info("Worker completed workflow execution", run_id=str(run_id), status=final_state.status.value)
            return final_state.status == WorkflowStatus.COMPLETED

        except Exception as e:
            logger.error("Worker task execution unhandled error", run_id=str(run_id), error=str(e))
            WORKFLOW_RUNS_TOTAL.labels(status="failed").inc()
            return False

        finally:
            await LeaseManager.release_lease(run_id_str, self.consumer_name)
            WORKFLOW_ACTIVE_RUNS.dec()

    async def handle_retry_or_dlq(
        self,
        task_data: dict[str, Any],
        error: str,
        attempt: int = 1,
        max_attempts: int = 3,
    ) -> None:
        """Retry task with exponential backoff or send to Dead Letter Queue."""
        run_id = uuid.UUID(task_data["run_id"])
        tenant_id = uuid.UUID(task_data["tenant_id"])

        if attempt < max_attempts:
            delay = (2 ** (attempt - 1)) * 1.0  # 1s, 2s, 4s backoff
            logger.warning("Retrying task with backoff", run_id=str(run_id), attempt=attempt, delay_sec=delay)
            await asyncio.sleep(delay)
            await TaskScheduler.enqueue_workflow(run_id=run_id, tenant_id=tenant_id, priority=attempt)
        else:
            logger.error("Exhausted retries, sending task to DLQ", run_id=str(run_id))
            DLQ_SIZE.inc()
            await TaskScheduler.enqueue_dlq(
                run_id=run_id,
                node_id="worker",
                error=error,
                payload=task_data,
            )

    async def run_loop(self, poll_interval_seconds: float = 1.0, max_iterations: Optional[int] = None) -> None:
        """Worker main loop polling tasks and recovering orphaned workflows."""
        self.running = True
        logger.info("Started WorkflowWorker loop", consumer_name=self.consumer_name)

        iterations = 0
        while self.running:
            if max_iterations and iterations >= max_iterations:
                break
            iterations += 1

            # Check and re-enqueue orphaned workflows periodically
            try:
                orphans = await CheckpointStore.recover_orphaned_workflows()
                for run_id, tenant_id in orphans:
                    logger.info("Re-enqueuing orphaned workflow for recovery execution", run_id=str(run_id))
                    await TaskScheduler.enqueue_workflow(run_id=run_id, tenant_id=tenant_id)
            except Exception as e:
                logger.warning("Error recovering orphaned workflows", error=str(e))

            await asyncio.sleep(poll_interval_seconds)

        logger.info("Stopped WorkflowWorker loop")
