"""
Parallel Node execution logic — dispatches multiple child tasks concurrently (fan-out / fan-in).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from vortex.engine.nodes.base import BaseNode
from vortex.observability.logger import get_logger

if TYPE_CHECKING:
    from vortex.engine.state import WorkflowState

logger = get_logger(__name__)


class ParallelNode(BaseNode):
    async def execute(self, state: WorkflowState) -> dict[str, Any]:
        branches: list[str] = self.config.get("branches", [])
        logger.info("Executing Parallel node fan-out", node_id=self.id, branches=branches)
        return {
            "branches": branches,
            "status": "fan_out_dispatched",
        }
