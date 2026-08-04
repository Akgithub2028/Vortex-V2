"""
Simple Sequential LLM Workflow Chain Example using Vortex SDK.
"""

import asyncio
from vortex.sdk import VortexClient, Workflow


async def main():
    # 1. Define workflow DAG
    wf = Workflow(name="simple-sequential-chain")
    wf.add_llm_node(
        node_id="draft",
        prompt="Write a concise outline for an engineering blog post about {topic}.",
        model="openai/gpt-4o",
    )
    wf.add_llm_node(
        node_id="refine",
        prompt="Polish and expand this outline into 3 bullet points: {draft}",
        model="openai/gpt-4o",
        dependencies=["draft"],
    )

    # 2. Initialize client & run workflow
    client = VortexClient(base_url="http://localhost:8000")
    print(f"Submitting workflow '{wf.name}'...")

    run = await client.run_workflow(wf, input={"topic": "Durable AI Execution Engines"})
    print(f"Run ID: {run.id}")
    print(f"Status: {run.status}")
    print(f"Tokens Used: {run.total_tokens}")
    print(f"Total Cost: ${run.total_cost_usd:.6f}")
    print("\nFinal Output:")
    print(run.output)


if __name__ == "__main__":
    asyncio.run(main())
