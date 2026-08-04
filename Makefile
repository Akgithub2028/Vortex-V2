.PHONY: dev test lint type-check format install clean docker-up docker-down migrate

# ─── Development ───────────────────────────────────────────────────────────────

install:
	pip install -e ".[dev]"
	pre-commit install

dev:
	uvicorn vortex.api.main:create_app --factory --reload --host 0.0.0.0 --port 8000 --log-level debug

# ─── Quality ───────────────────────────────────────────────────────────────────

lint:
	ruff check src/ tests/
	ruff format --check src/ tests/

format:
	ruff check --fix src/ tests/
	ruff format src/ tests/

type-check:
	mypy src/vortex --ignore-missing-imports

# ─── Testing ───────────────────────────────────────────────────────────────────

test:
	pytest tests/unit -v --tb=short

test-all:
	pytest tests/ -v --tb=short

test-cov:
	pytest tests/ -v --cov=src/vortex --cov-report=term-missing --cov-report=html

# ─── Database ──────────────────────────────────────────────────────────────────

migrate:
	alembic upgrade head

migrate-create:
	alembic revision --autogenerate -m "$(msg)"

migrate-down:
	alembic downgrade -1

# ─── Docker ────────────────────────────────────────────────────────────────────

docker-up:
	docker compose -f docker/docker-compose.yml up -d

docker-down:
	docker compose -f docker/docker-compose.yml down

docker-build:
	docker compose -f docker/docker-compose.yml build

docker-logs:
	docker compose -f docker/docker-compose.yml logs -f

# ─── Cleanup ───────────────────────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf htmlcov/ .coverage dist/ build/ *.egg-info
