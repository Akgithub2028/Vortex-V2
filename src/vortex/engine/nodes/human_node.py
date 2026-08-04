"""
Human Node execution logic — pauses workflow execution for Human-in-the-loop (HITL) approval.
"""

from __future__ import annotations

from typing import Any

from vortex.engine.nodes.base import BaseNode
from vortex.engine.state import WorkflowState, WorkflowStatus
from vortex.observability.logger import get_logger

logger = get_logger(__name__)


class HumanNode(BaseNode):
    async def execute(self, state: WorkflowState) -> dict[str, Any]:
        prompt: str = self.config.get("prompt", "Human approval required.")
        timeout_hours: int = int(self.config.get("timeout_hours", 24))

        logger.info("Executing Human node — pausing workflow for approval", node_id=self.id)
        state.status = WorkflowStatus.AWAITING_APPROVAL

        return {
            "status": "awaiting_approval",
            "prompt": prompt,
            "timeout_hours": timeout_hours,
        }
