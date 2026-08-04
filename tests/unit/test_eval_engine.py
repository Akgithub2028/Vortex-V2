"""
Unit tests for Evaluation Engine Scorers and Batch Runner.
"""

import pytest

from vortex.eval.runner import DatasetItem, EvaluationRunner
from vortex.eval.scorers import FaithfulnessScorer, RelevanceScorer, ToxicityScorer, get_scorer


@pytest.mark.asyncio
async def test_get_scorer_registry():
    f_scorer = get_scorer("faithfulness")
    r_scorer = get_scorer("relevance")
    t_scorer = get_scorer("toxicity")
    assert isinstance(f_scorer, FaithfulnessScorer)
    assert isinstance(r_scorer, RelevanceScorer)
    assert isinstance(t_scorer, ToxicityScorer)

    fallback_scorer = get_scorer("nonexistent_scorer")
    assert isinstance(fallback_scorer, FaithfulnessScorer)


@pytest.mark.asyncio
async def test_faithfulness_scorer():
    scorer = FaithfulnessScorer(threshold=0.7)

    res = await scorer.score(
        output="PostgreSQL uses MVCC for concurrency control.",
        reference_context="PostgreSQL uses MVCC for concurrency control and transaction isolation.",
    )
    assert res.scorer_name == "faithfulness"
    assert res.score >= 0.7
    assert res.passed is True


@pytest.mark.asyncio
async def test_relevance_scorer():
    scorer = RelevanceScorer(threshold=0.7)

    res = await scorer.score(
        output="FastAPI is a modern async web framework for Python.",
        input_prompt="What is FastAPI Python web framework?",
    )
    assert res.scorer_name == "relevance"
    assert res.score >= 0.7
    assert res.passed is True


@pytest.mark.asyncio
async def test_toxicity_scorer():
    scorer = ToxicityScorer(threshold=0.8)

    safe_res = await scorer.score(output="The application executed cleanly.")
    assert safe_res.score == 1.0
    assert safe_res.passed is True


@pytest.mark.asyncio
async def test_evaluation_runner_batch():
    runner = EvaluationRunner(scorer_name="faithfulness", threshold=0.7)

    items = [
        DatasetItem(
            id="item-1",
            input="What is Redis?",
            output="Redis is an in-memory data structure store.",
            reference_context="Redis is an open-source in-memory key-value data store.",
        ),
        DatasetItem(
            id="item-2",
            input="What is Python?",
            output="Python is a high-level programming language.",
            reference_context="Python is an interpreted high-level general-purpose programming language.",
        ),
    ]

    summary = await runner.run_batch("test_dataset", items)

    assert summary.dataset_name == "test_dataset"
    assert summary.total_items == 2
    assert summary.passed_count == 2
    assert summary.mean_score >= 0.7
    assert len(summary.item_results) == 2
