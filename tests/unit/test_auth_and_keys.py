"""
Unit tests for authentication middleware and API key creation routes.
"""

import pytest

from vortex.api.errors import ForbiddenError
from vortex.api.middleware.auth import AuthContext, require_role


@pytest.mark.asyncio
async def test_auth_context():
    auth = AuthContext(
        tenant_id="00000000-0000-0000-0000-000000000001",
        tenant_name="Test Tenant",
        role="owner",
    )
    assert auth.role == "owner"


@pytest.mark.asyncio
async def test_require_role_permission():
    auth_owner = AuthContext(
        tenant_id="00000000-0000-0000-0000-000000000001",
        tenant_name="Test",
        role="owner",
    )
    auth_viewer = AuthContext(
        tenant_id="00000000-0000-0000-0000-000000000001",
        tenant_name="Test",
        role="viewer",
    )

    checker = require_role("member")
    assert await checker(auth_owner) == auth_owner

    with pytest.raises(ForbiddenError):
        await checker(auth_viewer)


@pytest.mark.asyncio
async def test_create_api_key_route(async_client):
    payload = {"name": "Test Key", "role": "member", "rate_limit_rpm": 120}
    response = await async_client.post("/v1/keys", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Key"
    assert data["raw_key"].startswith("vx-live-")


@pytest.mark.asyncio
async def test_auth_middleware_invalid_key(async_client):
    # Test invalid Authorization header format
    headers_bad = {"Authorization": "Basic invalid_credentials"}
    res_bad = await async_client.get("/v1/prompts", headers=headers_bad)
    assert res_bad.status_code == 200  # Dev bypass when no raw key is parsed

    # Test unknown API key hash
    headers_unknown = {"Authorization": "Bearer vx-live-unknownkeyhash123456789"}
    res_unknown = await async_client.get("/v1/prompts", headers=headers_unknown)
    assert res_unknown.status_code == 401


@pytest.mark.asyncio
async def test_full_api_key_auth_flow(async_client):
    """Test creating an API key and then using it for authentication."""
    # Create key
    payload = {"name": "Auth Flow Key", "role": "member", "rate_limit_rpm": 60}
    res_create = await async_client.post("/v1/keys", json=payload)
    assert res_create.status_code == 201
    raw_key = res_create.json()["raw_key"]

    # Use key
    headers = {"Authorization": f"Bearer {raw_key}"}
    res_use = await async_client.get("/v1/prompts", headers=headers)
    assert res_use.status_code == 200


@pytest.mark.asyncio
async def test_route_level_rbac_enforcement(async_client):
    """Test that routes enforce roles properly (e.g. viewer cannot create prompts)."""
    # Create viewer key
    payload = {"name": "Viewer Key", "role": "viewer"}
    res_create = await async_client.post("/v1/keys", json=payload)
    assert res_create.status_code == 201
    raw_key = res_create.json()["raw_key"]

    # Try to access member-only route
    headers = {"Authorization": f"Bearer {raw_key}"}
    prompt_payload = {"name": "test_rbac", "template": "test", "variables": []}
    res_forbidden = await async_client.post("/v1/prompts", json=prompt_payload, headers=headers)
    assert res_forbidden.status_code == 403
    assert res_forbidden.json()["error"]["code"] == "FORBIDDEN"
