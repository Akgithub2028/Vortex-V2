"""
API key management routes.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from vortex.api.deps import AuthContext, require_role
from vortex.storage.database import get_session
from vortex.storage.models import ApiKey

router = APIRouter(prefix="/v1/keys", tags=["API Keys"])


class CreateKeyRequest(BaseModel):
    name: str
    role: str = "member"  # owner | member | viewer
    rate_limit_rpm: int = 60


class KeyCreatedResponse(BaseModel):
    id: uuid.UUID
    name: str
    key_prefix: str
    raw_key: str  # Displayed only once upon creation
    role: str


@router.post(
    "",
    response_model=KeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key",
)
async def create_api_key(
    request: CreateKeyRequest,
    auth: AuthContext = Depends(require_role("owner")),
) -> KeyCreatedResponse:
    raw_secret = secrets.token_hex(24)
    raw_key = f"vx-live-{raw_secret}"
    key_prefix = raw_key[:12]
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    key_id = uuid.uuid4()
    async with get_session() as session:
        api_key = ApiKey(
            id=key_id,
            tenant_id=auth.tenant_id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=request.name,
            role=request.role,
            rate_limit_rpm=request.rate_limit_rpm,
        )
        session.add(api_key)

    return KeyCreatedResponse(
        id=key_id,
        name=request.name,
        key_prefix=key_prefix,
        raw_key=raw_key,
        role=request.role,
    )
