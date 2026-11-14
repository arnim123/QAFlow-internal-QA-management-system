"""Odoo task mirror. These columns are storage; write-back is a later job."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Integer,
    Numeric,
    String,
    Unicode,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import Index, UniqueConstraint

from app.models.base import AuditMixin, Base, fk, indexes


class OdooTask(AuditMixin, Base):
    __tablename__ = "odoo_tasks"
    __table_args__ = (
        UniqueConstraint("odoo_id", name="uq_odoo_tasks_odoo_id"),
        Index("ix_odoo_tasks_stage_deadline", "odoo_stage", "deadline"),
        *indexes("odoo_tasks", "module_id", "assigned_tester_id", "created_by"),
    )

    odoo_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(Unicode(500), nullable=False)
    module_id: Mapped[int | None] = mapped_column(
        fk("modules.id", "fk_odoo_tasks_module_id_modules"),
        nullable=True,
    )
    priority: Mapped[str | None] = mapped_column(Unicode(32), nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    odoo_stage: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    assigned_tester_id: Mapped[int | None] = mapped_column(
        fk("users.id", "fk_odoo_tasks_assigned_tester_id_users"),
        nullable=True,
    )
    task_sub_status: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    estimated_hours: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    actual_hours: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    qa_started: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )
    qa_passed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )
    qa_cycles: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    description_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    checklist: Mapped[list | None] = mapped_column(JSON, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    raw: Mapped[dict | None] = mapped_column(JSON, nullable=True)
