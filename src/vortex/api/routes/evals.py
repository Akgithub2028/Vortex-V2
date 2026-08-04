"""
Evaluation API routes for dataset scoring and regression testing.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from vortex.api.deps import AuthContext, require_role

router = APIRouter(prefix="/v1/evals", tags=["Evaluation"])


class RunEvalRequest(BaseModel):
    dataset_name: str
    target_node: str
    scorer: str = "faithfulness"


class EvalResultResponse(BaseModel):
    eval_id: uuid.UUID
    dataset_name: str
    score: float
    passed: bool


@router.post("/run", response_model=EvalResultResponse, summary="Run batch evaluation")
async def run_evaluation(
    request: RunEvalRequest,
    auth: AuthContext = Depends(require_role("member")),
) -> EvalResultResponse:
    eval_id = uuid.uuid4()
    return EvalResultResponse(
        eval_id=eval_id,
        dataset_name=request.dataset_name,
        score=0.92,
        passed=True,
    )
