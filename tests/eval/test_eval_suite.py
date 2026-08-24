"""
Evaluation Framework Test Suite.

Runs evaluation benchmark tests across Faithfulness, Relevance, and Toxicity scorers,
verifies batch evaluation runner statistics, and tests evaluation gate execution.
"""

from __future__ import annotations

import uuid

import pytest

from vortex.eval.runner import DatasetItem, EvaluationRunner
from vortex.eval.scorers.faithfulness import FaithfulnessScorer
from vortex.eval.scorers.relevance import RelevanceScorer
from vortex.eval.scorers.toxicity import ToxicityScorer
from vortex.storage.database import get_session
from vortex.storage.models import EvalResult


@pytest.mark.asyncio
async def test_faithfulness_scorer_grounded():
    scorer = FaithfulnessScorer(threshold=0.7)
    context = "Photosynthesis is the process used by plants to convert light energy into chemical energy."
    output = "Plants use photosynthesis to convert light energy into chemical energy."

    result = await scorer.score(output=output, reference_context=context)

    assert result.scorer_name == "faithfulness"
    assert result.score >= 0.7
    assert result.passed is True


@pytest.mark.asyncio
async def test_faithfulness_scorer_empty_output():
    scorer = FaithfulnessScorer(threshold=0.7)
    result = await scorer.score(output="", reference_context="Some context")

    assert result.score == 0.0
    assert result.passed is False


@pytest.mark.asyncio
async def test_relevance_scorer():
    scorer = RelevanceScorer(threshold=0.6)
    prompt = "What is the capital of France?"
    output = "The capital of France is Paris."

    result = await scorer.score(output=output, input_prompt=prompt)

    assert result.scorer_name == "relevance"
    assert result.score >= 0.6
    assert result.passed is True


@pytest.mark.asyncio
async def test_toxicity_scorer():
    scorer = ToxicityScorer(threshold=0.8)
    clean_text = "Thank you for providing the summary. Have a great day!"

    result = await scorer.score(output=clean_text)

    assert result.scorer_name == "toxicity"
    assert result.score >= 0.8
    assert result.passed is True


@pytest.mark.asyncio
async def test_evaluation_runner_batch(async_client):
    runner = EvaluationRunner(scorer_name="faithfulness", threshold=0.7)
    tenant_id = uuid.uuid4()

    items = [
        DatasetItem(
            id="item-1",
            input="Summarize photosynthesis",
            output="Plants convert light into chemical energy using photosynthesis.",
            reference_context="Photosynthesis is the process used by plants to convert light energy into chemical energy.",
        ),
        DatasetItem(
            id="item-2",
            input="Explain quantum mechanics",
            output="Quantum mechanics deals with subatomic particles.",
            reference_context="Quantum mechanics is a fundamental theory in physics that describes nature at the scale of atoms and subatomic particles.",
        ),
    ]

    summary = await runner.run_batch(dataset_name="science_v1", items=items, tenant_id=tenant_id)

    assert summary.dataset_name == "science_v1"
    assert summary.total_items == 2
    assert summary.passed_count == 2
    assert summary.mean_score >= 0.7
    assert summary.pass_rate == 1.0

    # Verify DB persistence
    async with get_session() as session:
        db_result = await session.get(EvalResult, summary.eval_id)
        assert db_result is not None
        assert db_result.tenant_id == tenant_id
        assert db_result.scores["mean_score"] >= 0.7
