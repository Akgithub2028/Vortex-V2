"""
Prompt Template Registry API Routes.

GET /v1/prompts — List prompt templates
POST /v1/prompts — Create or version a prompt template
GET /v1/prompts/{name} — Get latest or specific version of prompt template
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from vortex.api.deps import get_current_auth, require_role
from vortex.api.errors import NotFoundError
from vortex.api.middleware.auth import AuthContext
from vortex.observability.logger import get_logger
from vortex.storage.database import get_session
from vortex.storage.models import PromptTemplate

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/prompts", tags=["Prompt Registry"])


class CreatePromptRequest(BaseModel):
    name: str = Field(..., example="research_summary_v1")
    template: str = Field(..., example="Summarize the following topic: {topic}")
    variables: List[str] = Field(default_factory=list, example=["topic"])


class PromptTemplateResponse(BaseModel):
    id: uuid.UUID
    name: str
    version: int
    template: str
    variables: List[str]
    created_at: str


@router.post(
    "",
    response_model=PromptTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or version a prompt template",
)
async def create_prompt_template(
    body: CreatePromptRequest,
    auth: AuthContext = Depends(require_role("member")),
) -> PromptTemplateResponse:
    async with get_session() as session:
        # Check current latest version for this template name
        stmt = select(PromptTemplate).where(
            PromptTemplate.tenant_id == auth.tenant_id,
            PromptTemplate.name == body.name,
        ).order_by(PromptTemplate.version.desc())
        res = await session.execute(stmt)
        existing = res.scalars().first()

        new_version = (existing.version + 1) if existing else 1
        prompt = PromptTemplate(
            tenant_id=auth.tenant_id,
            name=body.name,
            version=new_version,
            template=body.template,
            variables=body.variables,
        )
        session.add(prompt)

    logger.info("Registered prompt template", name=body.name, version=new_version, tenant=auth.tenant_name)
    return PromptTemplateResponse(
        id=prompt.id,
        name=prompt.name,
        version=prompt.version,
        template=prompt.template,
        variables=prompt.variables or [],
        created_at=prompt.created_at.isoformat(),
    )


@router.get(
    "",
    response_model=List[PromptTemplateResponse],
    summary="List all registered prompt templates for tenant",
)
async def list_prompt_templates(
    auth: AuthContext = Depends(get_current_auth),
) -> List[PromptTemplateResponse]:
    async with get_session() as session:
        stmt = select(PromptTemplate).where(PromptTemplate.tenant_id == auth.tenant_id).order_by(PromptTemplate.name)
        res = await session.execute(stmt)
        prompts = res.scalars().all()

        return [
            PromptTemplateResponse(
                id=p.id,
                name=p.name,
                version=p.version,
                template=p.template,
                variables=p.variables or [],
                created_at=p.created_at.isoformat(),
            )
            for p in prompts
        ]


@router.get(
    "/{name}",
    response_model=PromptTemplateResponse,
    summary="Get prompt template by name (latest version)",
)
async def get_prompt_template(
    name: str,
    version: Optional[int] = None,
    auth: AuthContext = Depends(get_current_auth),
) -> PromptTemplateResponse:
    async with get_session() as session:
        stmt = select(PromptTemplate).where(
            PromptTemplate.tenant_id == auth.tenant_id,
            PromptTemplate.name == name,
        )
        if version is not None:
            stmt = stmt.where(PromptTemplate.version == version)
        else:
            stmt = stmt.order_by(PromptTemplate.version.desc())

        res = await session.execute(stmt)
        prompt = res.scalars().first()

        if not prompt:
            raise NotFoundError("PromptTemplate", name)

        return PromptTemplateResponse(
            id=prompt.id,
            name=prompt.name,
            version=prompt.version,
            template=prompt.template,
            variables=prompt.variables or [],
            created_at=prompt.created_at.isoformat(),
        )
