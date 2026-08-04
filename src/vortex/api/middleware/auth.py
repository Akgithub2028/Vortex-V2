"""
Vortex authentication and authorization middleware / dependencies.

Supports:
- Header-based API keys (`Authorization: Bearer vx-live-...` or `X-API-Key: vx-live-...`)
- SHA-256 key hashing and lookup against `api_keys` table
- Development bypass mode when VORTEX_ENVIRONMENT == 'development' and no key provided
- RBAC permission checks (owner, member, viewer)
"""

from __future__ import annotations

import hashlib
import uuid

from fastapi import Depends, Header, Request
from pydantic import BaseModel
from sqlalchemy import select

from vortex.api.errors import ForbiddenError, UnauthorizedError
from vortex.config import Environment, get_settings
from vortex.observability.logger import get_logger
from vortex.storage.database import get_session
from vortex.storage.models import ApiKey, Tenant

logger = get_logger(__name__)


class AuthContext(BaseModel):
    """Authenticated tenant and user/key identity passed to route handlers."""

    tenant_id: uuid.UUID
    tenant_name: str
    key_id: uuid.UUID | None = None
    key_name: str = "default"
    role: str = "owner"  # owner | member | viewer
    is_dev: bool = False


def _hash_api_key(raw_key: str) -> str:
    """Compute SHA-256 hash of raw API key."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


async def get_current_auth(
    request: Request,
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None),
) -> AuthContext:
    """
    FastAPI dependency to extract and validate API key authentication.

    Header formats:
    - Authorization: Bearer vx-live-xyz123...
    - X-API-Key: vx-live-xyz123...
    """
    settings = get_settings()

    # Extract key from Authorization header or X-API-Key header
    raw_key = None
    if authorization and authorization.lower().startswith("bearer "):
        raw_key = authorization[7:].strip()
    elif x_api_key:
        raw_key = x_api_key.strip()

    # Dev bypass mode when running locally without a key
    if not raw_key:
        if settings.environment == Environment.DEVELOPMENT or settings.is_testing:
            logger.debug("Dev auth bypass active")
            # Return a synthetic dev context (ensuring a default dev tenant exists)
            dev_tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
            async with get_session() as session:
                dev_tenant = await session.get(Tenant, dev_tenant_id)
                if not dev_tenant:
                    dev_tenant = Tenant(
                        id=dev_tenant_id,
                        name="Default Dev Tenant",
                    )
                    session.add(dev_tenant)

            return AuthContext(
                tenant_id=dev_tenant_id,
                tenant_name="Default Dev Tenant",
                role="owner",
                is_dev=True,
            )
        raise UnauthorizedError("Missing API key. Provide via Bearer token or X-API-Key header.")

    # Hash incoming key
    key_hash = _hash_api_key(raw_key)

    # Query DB for matching active key
    async with get_session() as session:
        stmt = (
            select(ApiKey, Tenant)
            .join(Tenant, ApiKey.tenant_id == Tenant.id)
            .where(ApiKey.key_hash == key_hash, ApiKey.is_active == True)  # noqa: E712
        )
        result = await session.execute(stmt)
        row = result.first()

        if not row:
            raise UnauthorizedError("Invalid or inactive API key.")

        api_key, tenant = row

        return AuthContext(
            tenant_id=tenant.id,
            tenant_name=tenant.name,
            key_id=api_key.id,
            key_name=api_key.name,
            role=api_key.role,
        )


def require_role(min_role: str):
    """
    FastAPI dependency generator for RBAC role enforcement.

    Role hierarchy: owner > member > viewer

    Usage:
        @router.post("/workflows", dependencies=[Depends(require_role("member"))])
    """
    role_weights = {"viewer": 1, "member": 2, "owner": 3}

    async def _role_checker(auth: AuthContext = Depends(get_current_auth)) -> AuthContext:
        user_weight = role_weights.get(auth.role, 0)
        required_weight = role_weights.get(min_role, 3)

        if user_weight < required_weight:
            raise ForbiddenError(f"Role '{auth.role}' is insufficient. Required: '{min_role}'.")
        return auth

    return _role_checker
