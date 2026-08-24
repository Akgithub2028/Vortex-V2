"""
Vortex Client — Programmatic Async SDK for interacting with Vortex AI Execution Engine REST API.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

import httpx

from vortex.sdk.types import SDKPromptTemplateResponse, SDKWorkflowRunResponse
from vortex.sdk.workflow import Workflow


class VortexClient:
    """
    Async client for Vortex AI Execution Engine API.

    Example:
        >>> client = VortexClient(base_url="http://localhost:8000", api_key="vx-live-...")
        >>> run = await client.run_workflow(workflow, input={"topic": "Quantum Computing"})
        >>> print(run.status, run.output)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.headers = {"Content-Type": "application/json"}
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

    def _get_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.base_url, headers=self.headers, timeout=self.timeout)

    async def run_workflow(
        self,
        workflow: Workflow | dict[str, Any],
        input: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> SDKWorkflowRunResponse:
        """Submit a workflow graph for execution."""
        dag = workflow.to_dict() if isinstance(workflow, Workflow) else workflow
        payload: dict[str, Any] = {"dag": dag, "input": input or {}}
        if idempotency_key:
            payload["idempotency_key"] = idempotency_key

        async with self._get_client() as client:
            resp = await client.post("/v1/workflows/run", json=payload)
            resp.raise_for_status()
            return SDKWorkflowRunResponse.model_validate(resp.json())

    async def get_workflow_run(self, run_id: uuid.UUID | str) -> SDKWorkflowRunResponse:
        """Fetch status and outputs for an existing workflow run."""
        async with self._get_client() as client:
            resp = await client.get(f"/v1/workflows/{run_id}")
            resp.raise_for_status()
            return SDKWorkflowRunResponse.model_validate(resp.json())

    async def cancel_workflow_run(self, run_id: uuid.UUID | str) -> SDKWorkflowRunResponse:
        """Cancel an in-flight workflow run."""
        async with self._get_client() as client:
            resp = await client.post(f"/v1/workflows/{run_id}/cancel")
            resp.raise_for_status()
            return SDKWorkflowRunResponse.model_validate(resp.json())

    async def approve_human_node(
        self,
        run_id: uuid.UUID | str,
        node_id: str,
        approved: bool = True,
        feedback: str | None = None,
    ) -> SDKWorkflowRunResponse:
        """Approve or reject a paused Human-in-the-Loop node."""
        payload = {"approved": approved, "feedback": feedback}
        async with self._get_client() as client:
            resp = await client.post(f"/v1/workflows/{run_id}/nodes/{node_id}/approve", json=payload)
            resp.raise_for_status()
            return SDKWorkflowRunResponse.model_validate(resp.json())

    async def create_prompt_template(
        self,
        name: str,
        template: str,
        variables: list[str] | None = None,
    ) -> SDKPromptTemplateResponse:
        """Register a new versioned prompt template."""
        payload = {"name": name, "template": template, "variables": variables or []}
        async with self._get_client() as client:
            resp = await client.post("/v1/prompts", json=payload)
            resp.raise_for_status()
            return SDKPromptTemplateResponse.model_validate(resp.json())
