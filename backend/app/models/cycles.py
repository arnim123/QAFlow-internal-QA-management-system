"""QA cycles and the documents captured or drafted for one cycle."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Unicode, UnicodeText, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, Base, fk, indexes
from app.models.enums import CycleOutcome, DraftStatus, SourceKind, sa_enum


class QaCycle(AuditMixin, Base):
    __tablename__ = "qa_cycles"
    __table_args__ = (
        UniqueConstraint("odoo_task_id", "cycle_no", name="uq_qa_cycles_task_cycle"),
        *indexes("qa_cycles", "odoo_task_id", "final_approved_by", "created_by"),
    )

    odoo_task_id: Mapped[int] = mapped_column(
        fk("odoo_tasks.id", "fk_qa_cycles_odoo_task_id_odoo_tasks"),
        nullable=False,
    )
    cycle_no: Mapped[int] = mapped_column(nullable=False)
    # SOP does not fix this vocabulary. See docs/OPEN_QUESTIONS.md.
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    qa_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    outcome: Mapped[CycleOutcome | None] = mapped_column(
        sa_enum(CycleOutcome, "outcome"),
        nullable=True,
    )
    final_approved_by: Mapped[int | None] = mapped_column(
        fk("users.id", "fk_qa_cycles_final_approved_by_users"),
        nullable=True,
    )
    final_approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class RequirementSource(AuditMixin, Base):
    __tablename__ = "requirement_sources"
    __table_args__ = indexes(
        "requirement_sources",
        "qa_cycle_id",
        "provided_by",
        "created_by",
    )

    qa_cycle_id: Mapped[int] = mapped_column(
        fk("qa_cycles.id", "fk_requirement_sources_qa_cycle_id_qa_cycles"),
        nullable=False,
    )
    kind: Mapped[SourceKind] = mapped_column(
        sa_enum(SourceKind, "kind"),
        nullable=False,
    )
    file_path: Mapped[str | None] = mapped_column(Unicode(1024), nullable=True)
    transcript_text: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    provided_by: Mapped[int] = mapped_column(
        fk("users.id", "fk_requirement_sources_provided_by_users"),
        nullable=False,
    )


class UserStory(AuditMixin, Base):
    __tablename__ = "user_stories"
    __table_args__ = indexes("user_stories", "qa_cycle_id", "template_id", "created_by")

    qa_cycle_id: Mapped[int] = mapped_column(
        fk("qa_cycles.id", "fk_user_stories_qa_cycle_id_qa_cycles"),
        nullable=False,
    )
    template_id: Mapped[int] = mapped_column(
        fk("templates.id", "fk_user_stories_template_id_templates"),
        nullable=False,
    )
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[DraftStatus] = mapped_column(
        sa_enum(DraftStatus, "status"),
        nullable=False,
    )


class Requirement(AuditMixin, Base):
    __tablename__ = "requirements"
    __table_args__ = indexes("requirements", "qa_cycle_id", "template_id", "created_by")

    qa_cycle_id: Mapped[int] = mapped_column(
        fk("qa_cycles.id", "fk_requirements_qa_cycle_id_qa_cycles"),
        nullable=False,
    )
    template_id: Mapped[int] = mapped_column(
        fk("templates.id", "fk_requirements_template_id_templates"),
        nullable=False,
    )
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[DraftStatus] = mapped_column(
        sa_enum(DraftStatus, "status"),
        nullable=False,
    )
