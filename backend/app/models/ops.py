"""Audit log, background jobs, and nothing else operational."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, UnicodeText, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import Index

from app.models.base import AuditMixin, Base, indexes
from app.models.enums import JobStatus, sa_enum


class AuditLog(AuditMixin, Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_entity", "entity", "entity_id"),
        *indexes("audit_log", "created_by"),
    )

    actor: Mapped[str] = mapped_column(String(320), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    before: Mapped[dict | None] = mapped_column("before", JSON, nullable=True)
    after: Mapped[dict | None] = mapped_column("after", JSON, nullable=True)


class Job(AuditMixin, Base):
    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_status_run_at", "status", "run_at"),
        *indexes("jobs", "created_by"),
    )

    job_type: Mapped[str] = mapped_column("type", String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        sa_enum(JobStatus, "status"),
        nullable=False,
    )
    run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    locked_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_error: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
