# Vortex API Reference

Vortex provides a fully-typed, OpenAPI-compliant REST interface.
- **Base URL**: `http://localhost:8000` (Default)
- **Data Format**: `application/json`
- **Authentication**: `Authorization: Bearer <token>` or `X-API-Key: <token>`

---

## 1. Workflows

### Submit Workflow Run
`POST /v1/workflows/run`
Submit a new workflow execution DAG.

**Request Body**:
```json
{
  "dag": {
    "name": "research-pipeline",
    "version": 1,
    "nodes": [
      { "id": "search", "type": "tool", "config": { "tool_name": "web_search" } },
      { "id": "synthesize", "type": "llm", "config": { "prompt": "{search}" }, "dependencies": ["search"] }
    ]
  },
  "input": { "query": "AI systems architecture" },
  "idempotency_key": "req-12345"
}
```

**Responses**:
- `201 Created`: Workflow submitted successfully. Returns `WorkflowRun` object.
- `401 Unauthorized`: Invalid or missing API key.
- `422 Unprocessable Entity`: Invalid DAG topological structure.

---

### Stream Workflow Real-Time Events
`POST /v1/workflows/stream`
Same payload as `/run`, but returns a **Server-Sent Events (SSE)** stream (`text/event-stream`).

**Stream Event Example**:
```text
event: node.started
data: {"node_id": "search", "timestamp": "2026-08-04T10:00:00Z"}

event: node.chunk
data: {"node_id": "synthesize", "content": "The architecture..."}

event: workflow.completed
data: {"run_id": "8f278669...", "status": "COMPLETED"}
```

---

### Get Workflow Run
`GET /v1/workflows/{run_id}`
Retrieve the full materialized state of a workflow run, including all node outputs, token counts, and cost metrics.

### Approve Human-In-The-Loop Node
`POST /v1/workflows/{run_id}/nodes/{node_id}/approve`
Resume a workflow stuck in `AWAITING_APPROVAL` state.

**Request Body**:
```json
{
  "approved": true,
  "feedback": "Approved for production release"
}
```

---

## 2. Model Gateway

### Direct Chat Completion
`POST /v1/models/chat`
OpenAI-compatible chat completion endpoint. Supports provider fallbacks, guardrails, and evaluation gates.

**Request Body**:
```json
{
  "model": "anthropic/claude-3-5-sonnet",
  "messages": [{"role": "user", "content": "Hello"}],
  "temperature": 0.7
}
```

**Response Headers (Custom)**:
- `X-Vortex-Provider`: The provider that ultimately served the request (useful if fallback occurred).
- `X-Vortex-Cache-Hit`: `true` or `false`
- `X-Vortex-Cost-USD`: `0.0024`

---

## 3. Prompts & Evals

### Create Prompt Template
`POST /v1/prompts`
Store versioned prompt templates in the database.

**Request Body**:
```json
{
  "name": "sales_email_generator",
  "template": "Write a sales email for {product} targeting {audience}.",
  "default_model": "openai/gpt-4o"
}
```

### Run Evaluation Batch
`POST /v1/evals/run`
Run deterministic scorers against a dataset to compute regression metrics.

---

## 4. API Keys & Multi-Tenancy

### Create API Key
`POST /v1/keys`
Requires an existing `owner` role API key.

**Request Body**:
```json
{
  "name": "marketing-team-key",
  "role": "member",
  "rate_limit_rpm": 120
}
```

**Response**:
```json
{
  "id": "a1b2c3d4...",
  "name": "marketing-team-key",
  "key_prefix": "vx-live-...",
  "raw_key": "vx-live-super-secret-string", 
  "role": "member"
}
```
*(Note: `raw_key` is only returned once upon creation).*
