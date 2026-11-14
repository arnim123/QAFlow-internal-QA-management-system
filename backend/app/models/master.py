"""Module master test cases. Changes add a version; cases are retired, not deleted."""

from sqlalchemy import JSON, Integer, String, Unicode, UnicodeText, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, Base, fk, indexes
from app.models.enums import CaseSource, MasterCaseStatus, sa_enum


class MasterTestCase(AuditMixin, Base):
    __tablename__ = "master_test_cases"
    __table_args__ = (
        UniqueConstraint("module_id", "case_no", name="uq_master_test_cases_module_case_no"),
        *indexes("master_test_cases", "module_id", "created_by"),
    )

    module_id: Mapped[int] = mapped_column(
        fk("modules.id", "fk_master_test_cases_module_id_modules"),
        nullable=False,
    )
    functional_area: Mapped[str] = mapped_column(Unicode(200), nullable=False)
    case_no: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(Unicode(500), nullable=False)
    steps: Mapped[list] = mapped_column(JSON, nullable=False)
    expected_result: Mapped[str] = mapped_column(UnicodeText, nullable=False)
    # SOP does not fix priority or type. See docs/OPEN_QUESTIONS.md.
    priority: Mapped[str | None] = mapped_column(Unicode(32), nullable=True)
    case_type: Mapped[str | None] = mapped_column("type", Unicode(64), nullable=True)
    status: Mapped[MasterCaseStatus] = mapped_column(
        sa_enum(MasterCaseStatus, "status"),
        nullable=False,
    )
    current_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    source: Mapped[CaseSource] = mapped_column(
        sa_enum(CaseSource, "source"),
        nullable=False,
    )


class MasterTestCaseVersion(AuditMixin, Base):
    __tablename__ = "master_test_case_versions"
    __table_args__ = (
        UniqueConstraint(
            "master_test_case_id",
            "version_no",
            name="uq_master_test_case_versions_case_version",
        ),
        *indexes(
            "master_test_case_versions",
            "master_test_case_id",
            "changed_by",
            "created_by",
        ),
    )

    master_test_case_id: Mapped[int] = mapped_column(
        fk(
            "master_test_cases.id",
            "fk_master_test_case_versions_master_test_case_id_master_test_cases",
        ),
        nullable=False,
    )
    version_no: Mapped[int] = mapped_column(nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    changed_by: Mapped[int] = mapped_column(
        fk("users.id", "fk_master_test_case_versions_changed_by_users"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(UnicodeText, nullable=False)
