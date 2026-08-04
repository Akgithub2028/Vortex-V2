"""
Answer Relevance Scorer.

Evaluates how directly the generated output addresses the user's input prompt.
"""

from __future__ import annotations

from vortex.eval.scorers.base import BaseScorer, EvalScoreResult
from vortex.observability.logger import get_logger
from vortex.observability.metrics import EVAL_SCORES

logger = get_logger(__name__)


class RelevanceScorer(BaseScorer):
    @property
    def scorer_name(self) -> str:
        return "relevance"

    async def score(
        self,
        output: str,
        input_prompt: str | None = None,
        reference_context: str | None = None,
    ) -> EvalScoreResult:
        if not input_prompt:
            return EvalScoreResult(
                scorer_name=self.scorer_name,
                score=1.0,
                passed=True,
                threshold=self.threshold,
                reasoning="No input prompt provided, skipping relevance evaluation.",
            )

        prompt_keywords = set(input_prompt.lower().split())
        output_keywords = set(output.lower().split())

        overlap = len(prompt_keywords.intersection(output_keywords))
        score = min(1.0, 0.5 + (overlap / max(1, len(prompt_keywords))) * 0.5)

        passed = score >= self.threshold
        EVAL_SCORES.labels(scorer_name=self.scorer_name).observe(score)

        return EvalScoreResult(
            scorer_name=self.scorer_name,
            score=score,
            passed=passed,
            threshold=self.threshold,
            reasoning=f"Evaluated relevance to prompt (keyword overlap score: {score:.2f}).",
        )
