"""
Type definitions for the Vortex Python SDK.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class SDKWorkflowRunResponse(BaseModel):
    """Execution run response returned by Vortex API."""

    id: uuid.UUID
    status: str
    input: Dict[str, Any] = Field(default_factory=dict)
    output: Optional[Dict[str, Any]] = None
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    created_at: str


class SDKPromptTemplateResponse(BaseModel):
    """Prompt template response from Vortex registry."""

    id: uuid.UUID
    name: str
    version: int
    template: str
    variables: List[str] = Field(default_factory=list)
    created_at: str
