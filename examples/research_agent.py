"""
Multi-step Research Agent Workflow with Tool Node using Vortex SDK.
"""

import asyncio
from vortex.sdk import VortexClient, Workflow


async def main():
    wf = Workflow(name="research-agent-pipeline")

    # Step 1: Execute search tool
    wf.add_tool_node(
        node_id="fetch_sources",
        tool_name="web_search",
        tool_args={"query": "{query}", "max_results": 3},
    )

    # Step 2: Synthesize search results with LLM
    wf.add_llm_node(
        node_id="synthesize",
        prompt="Based on these search results: {fetch_sources}, answer: {query}",
        model="openai/gpt-4o",
        dependencies=["fetch_sources"],
    )

    client = VortexClient(base_url="http://localhost:8000")
    print("Executing research pipeline...")

    run = await client.run_workflow(wf, input={"query": "Latest advances in protein structure prediction"})
    print(f"Run ID: {run.id} | Status: {run.status}")
    print(f"Cost: ${run.total_cost_usd:.6f}")
    print("Output:", run.output)


if __name__ == "__main__":
    asyncio.run(main())
