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

    await client.run_workflow(wf, input={"topic": "Durable AI Execution Engines"})


if __name__ == "__main__":
    asyncio.run(main())
