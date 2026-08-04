"""
Unit tests for Prompt Template Registry API routes.
"""

import pytest


@pytest.mark.asyncio
async def test_prompt_template_routes(async_client):
    # 1. Create prompt template v1
    payload = {
        "name": "test_prompt_v1",
        "template": "Hello {name}, welcome to {topic}.",
        "variables": ["name", "topic"],
    }
    res1 = await async_client.post("/v1/prompts", json=payload)
    assert res1.status_code == 201
    data1 = res1.json()
    assert data1["name"] == "test_prompt_v1"
    assert data1["version"] == 1

    # 2. Version prompt template (v2)
    res2 = await async_client.post("/v1/prompts", json=payload)
    assert res2.status_code == 201
    data2 = res2.json()
    assert data2["version"] == 2

    # 3. List prompt templates
    res_list = await async_client.get("/v1/prompts")
    assert res_list.status_code == 200
    prompts = res_list.json()
    assert len(prompts) >= 2

    # 4. Get latest prompt template
    res_get = await async_client.get("/v1/prompts/test_prompt_v1")
    assert res_get.status_code == 200
    assert res_get.json()["version"] == 2

    # 5. Get specific version prompt template
    res_v1 = await async_client.get("/v1/prompts/test_prompt_v1?version=1")
    assert res_v1.status_code == 200
    assert res_v1.json()["version"] == 1

    # 6. Get missing prompt template
    res_missing = await async_client.get("/v1/prompts/nonexistent_prompt")
    assert res_missing.status_code == 404
