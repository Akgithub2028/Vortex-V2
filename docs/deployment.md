# Vortex Production Deployment Guide

This guide details how to deploy **Vortex** (`vortex-ai`) in production environments using Kubernetes or Docker Compose.

---

## 1. Core Environment Variables

Copy `.env.example` to configure your environment. Vortex requires strict configuration in production.

```bash
# ─── Core Settings ───
VORTEX_ENVIRONMENT=production
VORTEX_LOG_LEVEL=INFO

# ─── Auth & Security ───
VORTEX_SECRET_KEY=generate_a_secure_32_byte_secret_here
VORTEX_JWT_SECRET_KEY=generate_a_secure_jwt_secret_here

# ─── PostgreSQL (Requires pgvector extension) ───
VORTEX_DATABASE_URL=postgresql+asyncpg://vortex_user:password@postgres.internal:5432/vortex_db
VORTEX_DATABASE_POOL_SIZE=20
VORTEX_DATABASE_MAX_OVERFLOW=10

# ─── Redis (Cache & LeaseManager) ───
VORTEX_REDIS_URL=redis://redis.internal:6379/0

# ─── Model Provider API Keys ───
VORTEX_OPENAI_API_KEY=sk-proj-...
VORTEX_ANTHROPIC_API_KEY=sk-ant-...

# ─── Observability ───
VORTEX_OTEL_ENABLED=true
VORTEX_OTEL_EXPORTER_ENDPOINT=http://otel-collector.internal:4317
```

---

## 2. Kubernetes (Enterprise Scale)

For high-scale enterprise deployments, separate the read-heavy API Gateway from the write-heavy Worker nodes.

### Infrastructure Prerequisites
1. **PostgreSQL 16**: Must have the `pgvector` extension installed for semantic caching. Use managed services like AWS RDS or GCP Cloud SQL. Ensure High Availability (HA) read replicas are configured if read models are heavily queried.
2. **Redis 7+**: Use Redis Cluster or a highly available setup (AWS ElastiCache). The `LeaseManager` relies on Redis for atomic locks; if Redis goes down, worker nodes will halt processing to prevent split-brain execution.

### Microservices
- **FastAPI API Gateway (`Dockerfile.api`)**: 
  Deploy as a `Deployment` behind an Ingress Controller. Configure Horizontal Pod Autoscaler (HPA) to target 70% CPU utilization. This layer is entirely stateless.
- **Worker Service (`Dockerfile.worker`)**: 
  Deploy as a `Deployment`. These workers consume the Redis Streams task queue and acquire leases. Scale these workers dynamically based on queue length (e.g., using KEDA).

### OpenTelemetry Sidecars
Vortex has native OpenTelemetry instrumentation. Deploy an OTel Collector sidecar or DaemonSet in your cluster to collect traces from both the API and Worker nodes. Traces are exported via OTLP gRPC.

---

## 3. Docker Compose (Single Node Production)

For smaller deployments or testing, you can run the entire stack on a single beefy VM (e.g., AWS EC2 or DigitalOcean Droplet) behind a reverse proxy like Traefik or Caddy.

```bash
# Start all services (PostgreSQL, Redis, API, Worker)
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d --build
```
