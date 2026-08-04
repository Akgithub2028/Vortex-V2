"""
Human-in-the-Loop (HITL) Workflow Pause & Approve Example using Vortex SDK.
"""

import asyncio

from vortex.sdk import VortexClient, Workflow


async def main():
    wf = Workflow(name="deploy-approval-pipeline")

    # Step 1: Human Approval Gate
    wf.add_human_node(
        node_id="reviewer_signoff",
        instructions="Please verify code quality before production deployment.",
    )

    # Step 2: Tool Deployment node
    wf.add_tool_node(
        node_id="deploy",
        tool_name="deploy_service",
        dependencies=["reviewer_signoff"],
    )

    client = VortexClient(base_url="http://localhost:8000")

    # 1. Submit workflow (will pause at HITL node)
    run = await client.run_workflow(wf, input={"environment": "production"})

    if run.status == "AWAITING_APPROVAL":
        await client.approve_human_node(
            run_id=run.id,
            node_id="reviewer_signoff",
            approved=True,
            feedback="Approved by Staff DevOps Lead",
        )


if __name__ == "__main__":
    asyncio.run(main())
