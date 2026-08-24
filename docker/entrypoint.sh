#!/bin/bash
set -e

echo "=== VoRTeX API Server Starting ==="
echo "Environment: ${VORTEX_ENVIRONMENT:-development}"
echo "Port: ${PORT:-8000}"

# Run database migrations (safe to run repeatedly — Alembic is idempotent)
echo "Running database migrations..."
alembic upgrade head 2>/dev/null || echo "⚠ Migration skipped (no alembic config or DB not ready yet)"

# Start the API server, binding to Railway's injected $PORT (default 8000)
LOG_LEVEL="${VORTEX_LOG_LEVEL:-info}"
LOG_LEVEL="${LOG_LEVEL,,}"

exec uvicorn vortex.api.main:create_app \
  --factory \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --workers "${VORTEX_API_WORKERS:-1}" \
  --log-level "${LOG_LEVEL}"
