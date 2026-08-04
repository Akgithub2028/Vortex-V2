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
    print("1. Submitting HITL workflow...")
    run = await client.run_workflow(wf, input={"environment": "production"})
    print(f"Run ID: {run.id} | Initial Status: {run.status}")

    if run.status == "AWAITING_APPROVAL":
        print("\n2. Simulating Human Approval...")
        resumed_run = await client.approve_human_node(
            run_id=run.id,
            node_id="reviewer_signoff",
            approved=True,
            feedback="Approved by Staff DevOps Lead",
        )
        print(f"3. Resumed Status: {resumed_run.status}")
        print("Final Output:", resumed_run.output)


if __name__ == "__main__":
    asyncio.run(main())
