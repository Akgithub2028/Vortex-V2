"""
SQLAlchemy ORM models for Vortex storage layer.

Defines tables for:
- Tenants
- ApiKeys
- WorkflowDefinitions
- WorkflowRuns
- NodeRuns
- EvalDatasets
- EvalResults
- PromptTemplates
- AuditLog
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BIGINT,
    BOOLEAN,
    DECIMAL,
    INTEGER,
    JSON,
    TEXT,
    TIMESTAMP,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from vortex.storage.database import Base

if TYPE_CHECKING:
    from datetime import datetime


class UUIDType(TypeDecorator):
    """Platform-independent UUID type. Uses PostgreSQL native UUID, otherwise String(36)."""

    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            return str(uuid.UUID(str(value)))
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            return uuid.UUID(str(value))
        return value


# DB-agnostic JSON column type (JSONB on PostgreSQL, JSON on SQLite)
JSONType = JSON().with_variant(JSONB, "postgresql")


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    monthly_budget_usd: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    api_keys: Mapped[list[ApiKey]] = relationship("ApiKey", back_populates="tenant", cascade="all, delete-orphan")
    workflows: Mapped[list[WorkflowDefinition]] = relationship("WorkflowDefinition", back_populates="tenant", cascade="all, delete-orphan")
    runs: Mapped[list[WorkflowRun]] = relationship("WorkflowRun", back_populates="tenant", cascade="all, delete-orphan")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="member")  # owner | member | viewer
    rate_limit_rpm: Mapped[int] = mapped_column(INTEGER, default=60, nullable=False)
    is_active: Mapped[bool] = mapped_column(BOOLEAN, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    # Relationships
    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="api_keys")

    __table_args__ = (
        Index("idx_api_keys_hash", "key_hash"),
        Index("idx_api_keys_tenant", "tenant_id"),
    )


class WorkflowDefinition(Base):
    __tablename__ = "workflow_definitions"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(INTEGER, nullable=False, default=1)
    dag: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="workflows")
    runs: Mapped[list[WorkflowRun]] = relationship("WorkflowRun", back_populates="definition")

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", "version", name="uq_workflow_tenant_name_version"),
        Index("idx_workflow_defs_tenant", "tenant_id"),
    )


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    definition_id: Mapped[uuid.UUID | None] = mapped_column(UUIDType, ForeignKey("workflow_definitions.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="PENDING"
    )  # PENDING | RUNNING | COMPLETED | FAILED | CANCELLED | AWAITING_APPROVAL
    input: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    checkpoint: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    total_tokens: Mapped[int] = mapped_column(INTEGER, default=0, nullable=False)
    total_cost_usd: Mapped[Decimal] = mapped_column(DECIMAL(10, 6), default=Decimal("0.0"), nullable=False)
    max_cost_usd: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 2), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="runs")
    definition: Mapped[WorkflowDefinition | None] = relationship("WorkflowDefinition", back_populates="runs")
    node_runs: Mapped[list[NodeRun]] = relationship("NodeRun", back_populates="workflow_run", cascade="all, delete-orphan")
    events: Mapped[list[WorkflowEvent]] = relationship("WorkflowEvent", back_populates="workflow_run", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_run_tenant_idempotency"),
        Index("idx_workflow_runs_tenant_status", "tenant_id", "status"),
        Index("idx_workflow_runs_heartbeat", "status", "heartbeat_at"),
    )


class NodeRun(Base):
    __tablename__ = "node_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False)
    node_id: Mapped[str] = mapped_column(String(255), nullable=False)
    node_type: Mapped[str] = mapped_column(String(50), nullable=False)  # llm | tool | branch | parallel | eval | human
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING")
    input: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    error: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    retry_count: Mapped[int] = mapped_column(INTEGER, default=0, nullable=False)
    tokens_in: Mapped[int | None] = mapped_column(INTEGER, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(INTEGER, nullable=True)
    cost_usd: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 6), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cache_hit: Mapped[bool] = mapped_column(BOOLEAN, default=False, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(INTEGER, nullable=True)
    eval_scores: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    guardrail_results: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    workflow_run: Mapped[WorkflowRun] = relationship("WorkflowRun", back_populates="node_runs")

    __table_args__ = (
        Index("idx_node_runs_run_id", "run_id"),
        Index("idx_node_runs_type_status", "node_type", "status"),
    )


class WorkflowEvent(Base):
    __tablename__ = "workflow_events"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    run_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False)
    sequence_number: Mapped[int] = mapped_column(INTEGER, nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_data: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    timestamp: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    workflow_run: Mapped[WorkflowRun] = relationship("WorkflowRun", back_populates="events")

    __table_args__ = (
        UniqueConstraint("run_id", "sequence_number", name="uq_event_run_seq"),
        Index("idx_events_run_seq", "run_id", "sequence_number"),
        Index("idx_events_type", "event_type"),
    )


class EvalDataset(Base):
    __tablename__ = "eval_datasets"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(INTEGER, nullable=False, default=1)
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSONType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)


class EvalResult(Base):
    __tablename__ = "eval_results"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(UUIDType, ForeignKey("eval_datasets.id", ondelete="SET NULL"), nullable=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUIDType, ForeignKey("workflow_runs.id", ondelete="SET NULL"), nullable=True)
    scores: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    item_results: Mapped[list[dict[str, Any]]] = mapped_column(JSONType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(INTEGER, nullable=False, default=1)
    template: Mapped[str] = mapped_column(TEXT, nullable=False)
    variables: Mapped[list[str]] = mapped_column(JSONType, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (UniqueConstraint("tenant_id", "name", "version", name="uq_prompt_tenant_name_version"),)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUIDType, nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUIDType, nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUIDType, nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONType, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (Index("idx_audit_tenant_created", "tenant_id", "created_at"),)
