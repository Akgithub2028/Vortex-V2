"""
Simple Sequential LLM Workflow Chain Example using Vortex SDK.
"""

import asyncio
import os

from vortex.sdk import VortexClient, Workflow


async def main():
    base_url = os.getenv("VORTEX_API_URL", "https://vortex-v2-production.up.railway.app")
    api_key = os.getenv("VORTEX_API_KEY", "vtx_live_dev")

    # 1. Define workflow DAG
    wf = Workflow(name="simple-sequential-chain")
    wf.add_llm_node(
        node_id="draft",
        prompt="Write a concise outline for an engineering blog post about {topic}.",
        model="nvidia/meta/llama-3.1-70b-instruct",
    )
    wf.add_llm_node(
        node_id="refine",
        prompt="Polish and expand this outline into 3 bullet points.",
        model="nvidia/meta/llama-3.1-70b-instruct",
        dependencies=["draft"],
    )

    # 2. Initialize SDK client & run workflow
    print(f"🚀 Connecting to Vortex API at: {base_url}")
    client = VortexClient(base_url=base_url, api_key=api_key)
    run = await client.run_workflow(wf, input={"topic": "Durable AI Execution Engines"})

    print(f"✅ Workflow Run Completed! ID: {run.id}")
    print(f"📊 Status: {run.status} | Total Tokens: {run.total_tokens} | Cost: ${run.total_cost_usd:.6f}")
    print("📝 Final Output:", run.output)


if __name__ == "__main__":
    asyncio.run(main())
