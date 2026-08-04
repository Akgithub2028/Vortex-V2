"""
OpenAI-compatible Model Gateway chat completion endpoint.

POST /v1/models/chat — Execute direct model completion through gateway
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from vortex.api.deps import AuthContext, require_role
from vortex.gateway.providers.base import CompletionRequest, CompletionResponse
from vortex.gateway.router import ModelRouter

router = APIRouter(prefix="/v1/models", tags=["Models"])
model_router = ModelRouter()


@router.post("/chat", response_model=CompletionResponse, summary="Model chat completion")
async def chat_completion(
    request: CompletionRequest,
    auth: AuthContext = Depends(require_role("member")),
) -> CompletionResponse:
    return await model_router.complete(request)
