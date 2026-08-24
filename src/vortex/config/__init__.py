"""
Vortex configuration — single source of truth for all settings.

All configuration is driven by environment variables with sensible defaults.
Uses pydantic-settings for validation, type coercion, and .env file loading.
"""

from __future__ import annotations

from enum import Enum, StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """
    Central configuration object for the Vortex platform.

    Every field maps to an environment variable prefixed with VORTEX_.
    Example: VORTEX_DATABASE_URL sets database_url.
    """

    model_config = SettingsConfigDict(
        env_prefix="VORTEX_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── General ───────────────────────────────────────────────────────────────

    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    log_level: LogLevel = LogLevel.INFO
    service_name: str = "vortex"
    service_version: str = "0.1.0"

    # ─── API Server ────────────────────────────────────────────────────────────

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 1
    api_cors_origins: list[str] = Field(default=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://*.vercel.app",
        "https://*.up.railway.app",
    ])
    api_rate_limit_rpm: int = 60  # default requests per minute per API key

    # ─── Database (PostgreSQL) ─────────────────────────────────────────────────

    database_url: str = "postgresql+asyncpg://vortex:vortex@localhost:5432/vortex"
    database_pool_size: int = 20
    database_max_overflow: int = 10
    database_pool_recycle: int = 3600
    database_echo: bool = False

    # ─── Redis ─────────────────────────────────────────────────────────────────

    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 50
    redis_socket_timeout: float = 5.0
    redis_retry_on_timeout: bool = True

    # ─── Model Providers ───────────────────────────────────────────────────────

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""
    groq_api_key: str = ""
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_rate_limit_rpm: int = 40

    # Default model for LLM nodes when not specified
    default_model: str = "nvidia/meta/llama-3.1-70b-instruct"

    # Fallback chain: comma-separated model identifiers
    default_fallback_models: str = "anthropic/claude-3-5-sonnet-latest,openai/gpt-4o"

    # ─── Model Gateway ─────────────────────────────────────────────────────────

    gateway_max_retries: int = 3
    gateway_base_delay_seconds: float = 1.0
    gateway_max_delay_seconds: float = 60.0
    gateway_circuit_breaker_threshold: int = 5  # failures before circuit opens
    gateway_circuit_breaker_recovery_seconds: float = 30.0
    gateway_request_timeout_seconds: float = 120.0

    # ─── Semantic Cache ────────────────────────────────────────────────────────

    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600
    cache_semantic_threshold: float = 0.97  # cosine similarity threshold
    cache_embedding_model: str = "text-embedding-3-small"

    # ─── Workflow Engine ───────────────────────────────────────────────────────

    engine_max_concurrent_nodes: int = 10
    engine_default_node_retries: int = 2
    engine_node_timeout_seconds: float = 300.0
    engine_checkpoint_interval: int = 1  # checkpoint after every N nodes
    engine_heartbeat_interval_seconds: float = 15.0
    engine_orphan_timeout_seconds: float = 120.0

    # ─── Guardrails ────────────────────────────────────────────────────────────

    guardrails_enabled: bool = True
    guardrails_default_action: str = "warn"  # warn | block
    guardrails_pii_enabled: bool = True
    guardrails_injection_enabled: bool = True

    # ─── Evaluation ────────────────────────────────────────────────────────────

    eval_default_scorer_model: str = "openai/gpt-4o-mini"
    eval_gate_default_threshold: float = 0.7
    eval_gate_default_action: str = "warn"  # warn | retry | block

    # ─── Observability ─────────────────────────────────────────────────────────

    otel_enabled: bool = False
    otel_exporter_endpoint: str = "http://localhost:4317"
    otel_export_interval_ms: int = 5000
    metrics_enabled: bool = True
    metrics_port: int = 9090

    # ─── Auth ──────────────────────────────────────────────────────────────────

    jwt_secret_key: str = "CHANGE-ME-IN-PRODUCTION"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # ─── Blob Storage ──────────────────────────────────────────────────────────

    storage_backend: str = "local"  # local | s3
    storage_local_path: str = "./artifacts"
    storage_s3_bucket: str = ""
    storage_s3_region: str = "us-east-1"

    # ─── Derived ───────────────────────────────────────────────────────────────

    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION

    @property
    def is_testing(self) -> bool:
        return self.environment == Environment.TESTING

    @property
    def sync_database_url(self) -> str:
        """SQLAlchemy sync URL for Alembic migrations."""
        return self.database_url.replace("+asyncpg", "")

    @field_validator("database_url")
    @classmethod
    def _fix_asyncpg_sslmode(cls, v: str) -> str:
        """SQLAlchemy's asyncpg dialect requires ssl=require instead of sslmode=require."""
        if "+asyncpg" in v and "sslmode=" in v:
            return v.replace("sslmode=", "ssl=")
        return v

    @field_validator("jwt_secret_key")
    @classmethod
    def _warn_default_secret(cls, v: str) -> str:
        if v == "CHANGE-ME-IN-PRODUCTION":
            import warnings

            warnings.warn(
                "VORTEX_JWT_SECRET_KEY is using the default value. Set a strong secret in production.",
                UserWarning,
                stacklevel=2,
            )
        return v

    @model_validator(mode="after")
    def _set_debug_from_env(self) -> Settings:
        if self.environment == Environment.DEVELOPMENT:
            self.debug = True
            self.database_echo = True
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached singleton Settings instance.

    Call get_settings.cache_clear() in tests to reset.
    """
    return Settings()
