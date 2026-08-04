"""
RAG Workflow with Inline Faithfulness Evaluation Gate using Vortex SDK.
"""

import asyncio

from vortex.sdk import VortexClient, Workflow


async def main():
    wf = Workflow(name="rag-quality-eval-pipeline")

    # Step 1: LLM Generation node
    wf.add_llm_node(
        node_id="generate",
        prompt="Context: {context}\nQuestion: {question}\nAnswer:",
        model="openai/gpt-4o",
    )

    # Step 2: Inline Quality Evaluation Gate
    wf.add_eval_node(
        node_id="eval_faithfulness",
        target_node="generate",
        scorer_name="faithfulness",
        threshold=0.8,
        dependencies=["generate"],
    )

    client = VortexClient(base_url="http://localhost:8000")

    await client.run_workflow(
        wf,
        input={
            "context": "PostgreSQL 16 added support for pgvector IVFFlat and HNSW vector index acceleration.",
            "question": "What vector index algorithms does PostgreSQL 16 support via pgvector?",
        },
    )


if __name__ == "__main__":
    asyncio.run(main())
