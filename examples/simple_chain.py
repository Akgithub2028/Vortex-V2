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
        model="nvidia/meta/llama-3.1-70b-instruct",
    )
    wf.add_llm_node(
        node_id="refine",
        prompt="Polish and expand this outline into 3 key bullet points:\n\n{draft.text}",
        model="nvidia/meta/llama-3.1-70b-instruct",
        dependencies=["draft"],
    )

    # 2. Initialize SDK client & run workflow
    client = VortexClient(base_url="http://localhost:8000", api_key="vtx_live_dev")
    run = await client.run_workflow(wf, input={"topic": "Durable AI Execution Engines"})

    print(f"✅ Workflow Run Completed! ID: {run.id}")
    print(f"📊 Status: {run.status} | Total Tokens: {run.total_tokens} | Cost: ${run.total_cost_usd:.6f}")
    print("📝 Final Output:", run.output)


if __name__ == "__main__":
    asyncio.run(main())
