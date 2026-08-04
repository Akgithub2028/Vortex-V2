# Quickstart Guide — Vortex AI

Get up and running with **Vortex** (`vortex-ai`) locally in under 5 minutes.

---

## 1. Installation & Environment Setup

**Prerequisites:**
- **Python**: 3.12 or higher
- **Docker & Docker Compose** (for PostgreSQL + Redis runtime dependencies)

```bash
# Clone repository
git clone https://github.com/Akgithub2028/vortex.git
cd vortex

# Install Python SDK and dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Configure environment variables
cp .env.example .env
```

*Note: Edit `.env` to add your LLM Provider keys (e.g., `VORTEX_OPENAI_API_KEY`) if you plan to execute real models.*

---

## 2. Start Infrastructure & API Server

Launch the self-hostable PostgreSQL 16 (with pgvector) + Redis 7 stack via Docker Compose:

```bash
# Start DB and Cache services
make docker-up

# Run database migrations
make migrate

# Launch Vortex API Engine server (Dev mode bypasses Auth)
make dev
```

Verify system health:
```bash
curl http://localhost:8000/healthz
# Expected output: {"status":"ok","db":"ok","redis":"ok"}
```

---

## 3. Run Your First Workflow (Python SDK)

With the server running in Development mode, you don't need to pass an API key. 
Create a file `first_workflow.py`:

```python
import asyncio
from vortex.sdk import VortexClient, Workflow


async def main():
    # 1. Define a 2-step LLM DAG
    wf = Workflow(name="summary-pipeline")

    # Node 1: Draft
    wf.add_llm_node("draft", prompt="Outline 3 key benefits of {topic}.", model="openai/gpt-4o-mini")

    # Node 2: Polish (depends on 'draft')
    wf.add_llm_node("polish", prompt="Expand into final summary: {draft}", model="openai/gpt-4o-mini", dependencies=["draft"])

    # 2. Execute via Vortex Client
    client = VortexClient(base_url="http://localhost:8000")
    print(f"Submitting workflow for execution...")

    run = await client.run_workflow(wf, input={"topic": "Durable Workflow Orchestration"})

    print("✅ Execution Complete!")
    print(f"Run ID: {run.id}")
    print(f"Status: {run.status}")
    print(f"Tokens Used: {run.total_tokens}")
    print(f"Cost (USD): ${run.total_cost_usd:.4f}")
    print(f"Final Output: \n{run.output['polish']}")


if __name__ == "__main__":
    asyncio.run(main())
```

Execute your workflow:
```bash
python first_workflow.py
```

---

## 4. Open the Execution Console

Start the React Execution Console for visual debugging, OpenTelemetry span waterfall viewing, and cost tracking:

```bash
cd console
npm install
npm run dev
```

Navigate to `http://localhost:3000` in your browser to inspect live workflow runs!
