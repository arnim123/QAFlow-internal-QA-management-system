"""Per-cycle test sets, the review decision on each item, and review flags."""

from datetime import datetime

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Integer, String, UnicodeText, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import Index

from app.models.base import AuditMixin, Base, fk, indexes
from app.models.enums import ItemOrigin, ReviewDecision, SetStatus, sa_enum


class TaskTestSet(AuditMixin, Base):
    __tablename__ = "task_test_sets"
    __table_args__ = indexes("task_test_sets", "qa_cycle_id", "created_by")

    qa_cycle_id: Mapped[int] = mapped_column(
        fk("qa_cycles.id", "fk_task_test_sets_qa_cycle_id_qa_cycles"),
        nullable=False,
    )
    status: Mapped[SetStatus] = mapped_column(
        sa_enum(SetStatus, "status"),
        nullable=False,
    )


class TaskTestSetItem(AuditMixin, Base):
    __tablename__ = "task_test_set_items"
    __table_args__ = indexes(
        "task_test_set_items",
        "set_id",
        "master_case_id",
        "reviewed_by",
        "created_by",
    )

    set_id: Mapped[int] = mapped_column(
        fk("task_test_sets.id", "fk_task_test_set_items_set_id_task_test_sets"),
        nullable=False,
    )
    master_case_id: Mapped[int | None] = mapped_column(
        fk("master_test_cases.id", "fk_task_test_set_items_master_case_id_master_test_cases"),
        nullable=True,
    )
    proposed_case: Mapped[dict] = mapped_column(JSON, nullable=False)
    origin: Mapped[ItemOrigin] = mapped_column(
        sa_enum(ItemOrigin, "origin"),
        nullable=False,
    )
    review_decision: Mapped[ReviewDecision] = mapped_column(
        sa_enum(ReviewDecision, "review_decision"),
        nullable=False,
    )
    decision_reason: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(
        fk("users.id", "fk_task_test_set_items_reviewed_by_users"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    diff: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class ReviewFlag(AuditMixin, Base):
    __tablename__ = "review_flags"
    __table_args__ = (
        Index("ix_review_flags_entity", "entity_type", "entity_id"),
        Index("ix_review_flags_resolved", "resolved"),
        *indexes("review_flags", "created_by"),
    )

    rule_code: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    resolved: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )
