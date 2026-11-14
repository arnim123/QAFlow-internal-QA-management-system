"""GrokBot executions, AI results, and the tester's validation of each result."""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, String, UnicodeText, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, Base, fk, indexes
from app.models.enums import AiResult, ValidationDecision, sa_enum


class Execution(AuditMixin, Base):
    __tablename__ = "executions"
    __table_args__ = indexes("executions", "qa_cycle_id", "set_id", "created_by")

    qa_cycle_id: Mapped[int] = mapped_column(
        fk("qa_cycles.id", "fk_executions_qa_cycle_id_qa_cycles"),
        nullable=False,
    )
    set_id: Mapped[int] = mapped_column(
        fk("task_test_sets.id", "fk_executions_set_id_task_test_sets"),
        nullable=False,
    )
    executor: Mapped[str] = mapped_column(String(64), nullable=False)
    # SOP does not fix this vocabulary. See docs/OPEN_QUESTIONS.md.
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class ExecutionResult(AuditMixin, Base):
    __tablename__ = "execution_results"
    __table_args__ = (
        UniqueConstraint("execution_id", "item_id", name="uq_execution_results_execution_item"),
        *indexes("execution_results", "execution_id", "item_id", "created_by"),
    )

    execution_id: Mapped[int] = mapped_column(
        fk("executions.id", "fk_execution_results_execution_id_executions"),
        nullable=False,
    )
    item_id: Mapped[int] = mapped_column(
        fk("task_test_set_items.id", "fk_execution_results_item_id_task_test_set_items"),
        nullable=False,
    )
    ai_result: Mapped[AiResult] = mapped_column(
        sa_enum(AiResult, "ai_result"),
        nullable=False,
    )
    actual_behaviour: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class ResultValidation(AuditMixin, Base):
    __tablename__ = "result_validations"
    __table_args__ = (
        UniqueConstraint("result_id", name="uq_result_validations_result_id"),
        *indexes("result_validations", "result_id", "validated_by", "created_by"),
    )

    result_id: Mapped[int] = mapped_column(
        fk("execution_results.id", "fk_result_validations_result_id_execution_results"),
        nullable=False,
    )
    tester_result: Mapped[str] = mapped_column(String(32), nullable=False)
    decision: Mapped[ValidationDecision] = mapped_column(
        sa_enum(ValidationDecision, "decision"),
        nullable=False,
    )
    reproduced_manually: Mapped[bool] = mapped_column(Boolean, nullable=False)
    notes: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    validated_by: Mapped[int] = mapped_column(
        fk("users.id", "fk_result_validations_validated_by_users"),
        nullable=False,
    )
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
