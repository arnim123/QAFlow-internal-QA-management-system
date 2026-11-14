"""Versioned Excel reports attached to a QA cycle."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Unicode, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, Base, fk, indexes
from app.models.enums import ReportType, sa_enum


class Report(AuditMixin, Base):
    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint("qa_cycle_id", "type", "version", name="uq_reports_cycle_type_version"),
        *indexes("reports", "qa_cycle_id", "created_by"),
    )

    qa_cycle_id: Mapped[int] = mapped_column(
        fk("qa_cycles.id", "fk_reports_qa_cycle_id_qa_cycles"),
        nullable=False,
    )
    report_type: Mapped[ReportType] = mapped_column(
        "type",
        sa_enum(ReportType, "type"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    file_path: Mapped[str] = mapped_column(Unicode(1024), nullable=False)
    odoo_attachment_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
