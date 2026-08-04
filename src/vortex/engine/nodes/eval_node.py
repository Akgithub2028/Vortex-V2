"""
Eval Node execution logic — computes evaluation score and enforces quality gate thresholds using concrete evaluation scorers.
"""

from __future__ import annotations

from typing import Any

from vortex.engine.nodes.base import BaseNode
from vortex.engine.state import WorkflowState
from vortex.eval.scorers import get_scorer
from vortex.observability.logger import get_logger

logger = get_logger(__name__)


class EvalNode(BaseNode):
    async def execute(self, state: WorkflowState) -> dict[str, Any]:
        scorer_name: str = self.config.get("scorer", "faithfulness")
        threshold: float = float(self.config.get("threshold", 0.7))
        action: str = self.config.get("action", "warn")  # warn | retry | block
        target_node: str = self.config.get("target_node", "")

        target_output = state.completed_nodes.get(target_node, {})
        text_content = target_output.get("text", "") if isinstance(target_output, dict) else str(target_output)

        # Run concrete evaluation scorer
        scorer_inst = get_scorer(scorer_name, threshold)
        eval_res = await scorer_inst.score(
            output=text_content,
            input_prompt=state.variables.get("prompt"),
            reference_context=state.variables.get("context"),
        )

        logger.info(
            "Executing Eval node",
            node_id=self.id,
            scorer=scorer_name,
            score=eval_res.score,
            threshold=threshold,
            passed=eval_res.passed,
        )

        return {
            "scorer": scorer_name,
            "score": eval_res.score,
            "threshold": threshold,
            "passed": eval_res.passed,
            "reasoning": eval_res.reasoning,
            "action": action,
        }
