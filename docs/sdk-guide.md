# Vortex Python SDK Guide (`vortex-ai`)

The `vortex-ai` Python SDK provides a type-safe, fluent builder for constructing and running durable AI workflow graphs against the Vortex Execution Engine.

---

## 1. Installation

```bash
pip install vortex-ai
```

---

## 2. Defining a Workflow DAG

Vortex workflows are Directed Acyclic Graphs (DAGs) made of distinct node types. The engine automatically computes execution order based on the `dependencies` array.

```python
from vortex.sdk import Workflow

wf = Workflow(name="enterprise-research-pipeline", version=1)

# A. Tool Node (Fetches data)
wf.add_tool_node(node_id="search_web", tool_name="google_search", input_args={"query": "{topic}"})

# B. LLM Node (Inferences)
wf.add_llm_node(
    node_id="draft",
    prompt="Synthesize this research into a brief: {search_web}",
    model="anthropic/claude-3-5-sonnet",
    temperature=0.2,
    dependencies=["search_web"],
)

# C. Eval Node (Quality Gate)
wf.add_eval_node(node_id="quality_check", target_node="draft", scorer_name="faithfulness", threshold=0.85, dependencies=["draft"])
```

---

## 3. Submitting & Streaming Workflows

The `VortexClient` interacts with the Gateway. You can run synchronously (wait for completion) or stream real-time events.

### Synchronous Execution
```python
import asyncio
from vortex.sdk import VortexClient


async def run():
    client = VortexClient(base_url="http://localhost:8000", api_key="vx-live-...")
    run_state = await client.run_workflow(wf, input={"topic": "PostgreSQL Vector Search"})

    print(f"Status: {run_state.status}")
    print(f"Cost: ${run_state.total_cost_usd:.4f}")
    print(f"Final Output: {run_state.output}")


asyncio.run(run())
```

### Server-Sent Events (SSE) Streaming
To stream tokens to a UI in real-time as the LLM generates them:

```python
async def stream():
    client = VortexClient(base_url="http://localhost:8000", api_key="vx-live-...")
    
    async for event in client.stream_workflow(wf, input={"topic": "AI Agents"}):
        if event.type == "node.started":
            print(f"\n[{event.node_id}] started...")
        elif event.type == "node.chunk":
            print(event.content, end="", flush=True)
        elif event.type == "workflow.completed":
            print(f"\n\nWorkflow finished! Total Cost: ${event.data['total_cost_usd']}")
```

---

## 4. Human-in-the-Loop (HITL) Approvals

Workflows can pause indefinitely to await a human reviewer. This is highly useful for high-stakes actions like sending emails or executing SQL.

```python
# Check if workflow paused for human approval
if run_state.status == "AWAITING_APPROVAL":
    print("Workflow paused. Manual review required.")

    # ... Developer triggers this via UI/Slack ...
    resumed = await client.approve_human_node(run_id=run_state.id, node_id="reviewer_signoff", approved=True, feedback="Looks good to me!")
    print("Resumed status:", resumed.status)
```
Since Vortex is backed by a PostgreSQL event store, the execution engine perfectly rehydrates the state and continues exactly where it left off.
