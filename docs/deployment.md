# VoRTeX Production Deployment Guide

This guide covers deploying VoRTeX as a **Vercel + Railway hybrid** — the recommended production architecture for portfolio and small-scale SaaS usage.

---

## Architecture Overview

```text
┌──────────────────────────────────────────────────┐
│            VERCEL (Free Tier)                     │
│        React + Vite Console (SPA)                │
│     https://vortex-console.vercel.app            │
└───────────────────────┬──────────────────────────┘
                        │ HTTPS (fetch / SSE)
                        ▼
┌──────────────────────────────────────────────────┐
│          RAILWAY (Hobby Plan — $5/mo)            │
│    FastAPI API Gateway + Background Worker       │
│  https://vortex-api-production.up.railway.app    │
└──────────┬───────────────────────┬───────────────┘
           │                       │
           ▼                       ▼
┌─────────────────────┐  ┌────────────────────────┐
│  NEON.TECH (Free)   │  │  UPSTASH (Free)        │
│  PostgreSQL 16      │  │  Serverless Redis (TLS) │
└─────────────────────┘  └────────────────────────┘
```

**Monthly Cost:** $0–$5 total

---

## 1. Prerequisites

- **GitHub account** with the VoRTeX repository
- **NVIDIA NIM API key** (free at [build.nvidia.com](https://build.nvidia.com/))

---

## 2. Provision Managed Infrastructure

### 2.1 Neon.tech PostgreSQL (Free Tier)

1. Sign up at [neon.tech](https://neon.tech)
2. Create a new project: name `vortex`, region `US East (Ohio)`, PostgreSQL 16
3. Copy the connection string and convert to asyncpg format:
   ```
   postgresql+asyncpg://user:pass@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```

### 2.2 Upstash Redis (Free Tier)

1. Sign up at [upstash.com](https://upstash.com)
2. Create a Redis database: name `vortex-redis`, region `US-East-1`, TLS enabled
3. Copy the Redis URL (note `rediss://` with double-s for TLS):
   ```
   rediss://default:password@usw2-xxx.upstash.io:6379
   ```

---

## 3. Deploy Backend to Railway

### 3.1 Project Setup

1. Sign up at [railway.app](https://railway.app) with GitHub
2. Create a new project → Deploy from GitHub → Select `VoRTeX` repo
3. Railway will detect `railway.toml` and use the Dockerfile

### 3.2 Environment Variables

Set these in the Railway dashboard → Variables tab:

| Variable | Value |
|---|---|
| `VORTEX_ENVIRONMENT` | `production` |
| `VORTEX_DATABASE_URL` | `postgresql+asyncpg://...neon.tech/...?sslmode=require` |
| `VORTEX_REDIS_URL` | `rediss://...upstash.io:6379` |
| `VORTEX_NVIDIA_API_KEY` | `nvapi-...` |
| `VORTEX_JWT_SECRET_KEY` | *(generate with `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`)* |
| `VORTEX_API_CORS_ORIGINS` | `["https://vortex-console.vercel.app"]` |

> **Note:** Railway automatically injects the `PORT` variable. The entrypoint script reads `$PORT` to bind uvicorn.

### 3.3 Auto-Deploy from GitHub

1. In Railway dashboard → Account Settings → Tokens → Create a token (`github-ci-deploy`)
2. In GitHub repo → Settings → Secrets → Actions → New secret:
   - Name: `RAILWAY_TOKEN`, Value: *(paste Railway token)*
3. Every push to `main` now auto-deploys via `.github/workflows/deploy.yml`

---

## 4. Deploy Frontend to Vercel

### 4.1 Project Setup

1. Sign up at [vercel.com](https://vercel.com) with GitHub
2. Import the VoRTeX repository
3. **Set Root Directory to `console`**

### 4.2 Build Settings

| Setting | Value |
|---|---|
| Framework Preset | Vite |
| Root Directory | `console` |
| Build Command | `npm run build` |
| Output Directory | `dist` |

### 4.3 Environment Variables

| Variable | Value |
|---|---|
| `VITE_API_BASE_URL` | `https://vortex-api-production.up.railway.app` |

### 4.4 Deploy

Click Deploy. Vercel builds and serves the React SPA on its global edge CDN.

---

## 5. Verify Deployment

```bash
# Health check
curl https://vortex-api-production.up.railway.app/healthz

# Run a workflow
curl -X POST https://vortex-api-production.up.railway.app/v1/workflows/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: vtx_live_dev" \
  -d '{"name": "smoke-test", "dag": {"nodes": {"test": {"type": "llm", "config": {"prompt": "Hello, VoRTeX!"}}}}}'

# Prometheus metrics
curl https://vortex-api-production.up.railway.app/metrics
```

---

## 6. Local Development

For local development, use Docker Compose:

```bash
# Start PostgreSQL + Redis
docker compose -f docker/docker-compose.yml up -d postgres redis

# Run API server
make dev

# Run console
cd console && npm run dev
```

---

## 7. Environment Configuration Reference

See [.env.example](../.env.example) for all available environment variables with documentation.

### Key Environment Variables

| Variable | Default | Description |
|---|---|---|
| `VORTEX_ENVIRONMENT` | `development` | `development`, `staging`, `production`, `testing` |
| `VORTEX_DATABASE_URL` | `postgresql+asyncpg://...localhost...` | PostgreSQL connection (asyncpg) |
| `VORTEX_REDIS_URL` | `redis://localhost:6379/0` | Redis connection (`rediss://` for TLS) |
| `VORTEX_NVIDIA_API_KEY` | `""` | NVIDIA NIM API key |
| `VORTEX_JWT_SECRET_KEY` | `CHANGE-ME-IN-PRODUCTION` | JWT signing secret |
| `VORTEX_API_CORS_ORIGINS` | `["http://localhost:3000", ...]` | Allowed CORS origins (JSON array) |
| `PORT` | `8000` | Server port (injected by Railway) |
