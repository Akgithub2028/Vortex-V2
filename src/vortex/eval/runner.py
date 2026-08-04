"""
Batch Evaluation Runner.

Executes evaluation datasets across registered scorers, computes aggregated statistics,
and records results to PostgreSQL `eval_results` table.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from vortex.eval.scorers import get_scorer
from vortex.observability.logger import get_logger
from vortex.observability.metrics import EVAL_GATE_RESULTS_TOTAL
from vortex.storage.database import get_session
from vortex.storage.models import EvalResult

if TYPE_CHECKING:
    from vortex.eval.scorers.base import EvalScoreResult

logger = get_logger(__name__)


class DatasetItem(BaseModel):
    id: str
    input: str
    output: str
    reference_context: str | None = None


class BatchEvalSummary(BaseModel):
    eval_id: uuid.UUID
    dataset_name: str
    scorer_name: str
    total_items: int
    passed_count: int
    failed_count: int
    mean_score: float
    pass_rate: float
    item_results: list[dict[str, Any]] = Field(default_factory=list)


class EvaluationRunner:
    """Runs evaluation benchmarks across datasets."""

    def __init__(self, scorer_name: str = "faithfulness", threshold: float = 0.7):
        self.scorer_name = scorer_name
        self.scorer = get_scorer(scorer_name, threshold)

    async def run_batch(
        self,
        dataset_name: str,
        items: list[DatasetItem],
        tenant_id: uuid.UUID | None = None,
    ) -> BatchEvalSummary:
        eval_id = uuid.uuid4()
        total_items = len(items)
        scores: list[float] = []
        item_results: list[dict[str, Any]] = []
        passed_count = 0

        logger.info(
            "Starting batch evaluation run",
            eval_id=str(eval_id),
            dataset=dataset_name,
            total_items=total_items,
            scorer=self.scorer_name,
        )

        for item in items:
            res: EvalScoreResult = await self.scorer.score(
                output=item.output,
                input_prompt=item.input,
                reference_context=item.reference_context,
            )

            scores.append(res.score)
            if res.passed:
                passed_count += 1

            EVAL_GATE_RESULTS_TOTAL.labels(
                scorer_name=self.scorer_name,
                result="pass" if res.passed else "block",
            ).inc()

            item_results.append(
                {
                    "item_id": item.id,
                    "score": res.score,
                    "passed": res.passed,
                    "reasoning": res.reasoning,
                }
            )

        mean_score = sum(scores) / max(1, total_items)
        pass_rate = passed_count / max(1, total_items)

        summary = BatchEvalSummary(
            eval_id=eval_id,
            dataset_name=dataset_name,
            scorer_name=self.scorer_name,
            total_items=total_items,
            passed_count=passed_count,
            failed_count=total_items - passed_count,
            mean_score=mean_score,
            pass_rate=pass_rate,
            item_results=item_results,
        )

        # Persist summary to DB if tenant_id provided
        if tenant_id:
            async with get_session() as session:
                eval_record = EvalResult(
                    id=eval_id,
                    tenant_id=tenant_id,
                    scores={
                        "mean_score": mean_score,
                        "pass_rate": pass_rate,
                        "scorer": self.scorer_name,
                    },
                    item_results=item_results,
                )
                session.add(eval_record)

        logger.info(
            "Batch evaluation completed",
            eval_id=str(eval_id),
            mean_score=mean_score,
            pass_rate=pass_rate,
        )

        return summary
