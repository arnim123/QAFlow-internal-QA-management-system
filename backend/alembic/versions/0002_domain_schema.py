"""domain schema

Revision ID: 0002_domain_schema
Revises: 0001_empty_baseline
Create Date: 2026-11-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mssql

revision: str = "0002_domain_schema"
down_revision: str | None = "0001_empty_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = (
    "roles",
    "users",
    "api_keys",
    "modules",
    "templates",
    "settings",
    "odoo_tasks",
    "qa_cycles",
    "requirement_sources",
    "user_stories",
    "requirements",
    "master_test_cases",
    "master_test_case_versions",
    "task_test_sets",
    "task_test_set_items",
    "executions",
    "execution_results",
    "result_validations",
    "reports",
    "review_flags",
    "audit_log",
    "jobs",
)

_DROP_BEFORE_USERS = (
    "result_validations",
    "execution_results",
    "executions",
    "task_test_set_items",
    "task_test_sets",
    "reports",
    "user_stories",
    "requirements",
    "requirement_sources",
    "master_test_case_versions",
    "master_test_cases",
    "qa_cycles",
    "odoo_tasks",
    "templates",
    "modules",
    "review_flags",
    "audit_log",
    "jobs",
    "settings",
    "api_keys",
)

_ROLE_CODES = (
    "admin",
    "qa_lead",
    "tester",
    "requirement_provider",
    "viewer",
    "executor_bot",
)


def _audit() -> list[sa.Column]:
    return [
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("SYSDATETIMEOFFSET()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("SYSDATETIMEOFFSET()"),
        ),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("row_version", mssql.ROWVERSION(), nullable=False),
    ]


def _pk(table: str) -> sa.PrimaryKeyConstraint:
    return sa.PrimaryKeyConstraint("id", name=f"pk_{table}")


def _fk(column: str, target: str, name: str, *, nullable: bool) -> sa.Column:
    return sa.Column(
        column,
        sa.BigInteger(),
        sa.ForeignKey(target, name=name, ondelete="NO ACTION"),
        nullable=nullable,
    )


def _enum(column: str, *values: str) -> sa.Enum:
    return sa.Enum(
        *values,
        name=column,
        native_enum=False,
        create_constraint=True,
        length=32,
    )


def _created_by_indexes() -> None:
    for table in _TABLES:
        op.create_index(f"ix_{table}_created_by", table, ["created_by"])


def _created_by_foreign_keys() -> None:
    for table in _TABLES:
        op.create_foreign_key(
            f"fk_{table}_created_by_users",
            table,
            "users",
            ["created_by"],
            ["id"],
            ondelete="NO ACTION",
        )


def upgrade() -> None:
    op.create_table(
        "roles",
        *_audit(),
        sa.Column("code", _enum("code", *_ROLE_CODES), nullable=False),
        _pk("roles"),
        sa.UniqueConstraint("code", name="uq_roles_code"),
    )
    op.create_table(
        "users",
        *_audit(),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("display_name", sa.Unicode(200), nullable=False),
        _fk("role_id", "roles.id", "fk_users_role_id_roles", nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        _pk("users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_table(
        "api_keys",
        *_audit(),
        _fk("user_id", "users.id", "fk_api_keys_user_id_users", nullable=False),
        sa.Column("name", sa.Unicode(200), nullable=False),
        sa.Column("key_hash", sa.String(255), nullable=False),
        sa.Column("key_prefix", sa.String(32), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        _pk("api_keys"),
        sa.UniqueConstraint("key_hash", name="uq_api_keys_key_hash"),
    )
    op.create_table(
        "modules",
        *_audit(),
        sa.Column("name", sa.Unicode(200), nullable=False),
        sa.Column("overview", sa.UnicodeText(), nullable=True),
        sa.Column("functional_areas", sa.JSON(), nullable=False),
        _pk("modules"),
        sa.UniqueConstraint("name", name="uq_modules_name"),
    )
    op.create_table(
        "templates",
        *_audit(),
        sa.Column(
            "type",
            _enum(
                "type",
                "user_story",
                "requirement",
                "test_case",
                "execution_result",
                "report",
            ),
            nullable=False,
        ),
        sa.Column("json_schema", sa.JSON(), nullable=False),
        sa.Column("columns", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        _pk("templates"),
        sa.UniqueConstraint("type", "version", name="uq_templates_type_version"),
    )
    op.create_table(
        "settings",
        *_audit(),
        sa.Column("key", sa.String(128), nullable=False),
        sa.Column("value", sa.UnicodeText(), nullable=False),
        _pk("settings"),
        sa.UniqueConstraint("key", name="uq_settings_key"),
    )
    op.create_table(
        "odoo_tasks",
        *_audit(),
        sa.Column("odoo_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.Unicode(500), nullable=False),
        _fk("module_id", "modules.id", "fk_odoo_tasks_module_id_modules", nullable=True),
        sa.Column("priority", sa.Unicode(32), nullable=True),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("odoo_stage", sa.Unicode(255), nullable=True),
        _fk(
            "assigned_tester_id",
            "users.id",
            "fk_odoo_tasks_assigned_tester_id_users",
            nullable=True,
        ),
        sa.Column("task_sub_status", sa.Unicode(255), nullable=True),
        sa.Column("estimated_hours", sa.Numeric(12, 2), nullable=True),
        sa.Column("actual_hours", sa.Numeric(12, 2), nullable=True),
        sa.Column("qa_started", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("qa_passed", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("qa_cycles", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("description_hash", sa.String(64), nullable=True),
        sa.Column("checklist", sa.JSON(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw", sa.JSON(), nullable=True),
        _pk("odoo_tasks"),
        sa.UniqueConstraint("odoo_id", name="uq_odoo_tasks_odoo_id"),
    )
    op.create_table(
        "qa_cycles",
        *_audit(),
        _fk(
            "odoo_task_id",
            "odoo_tasks.id",
            "fk_qa_cycles_odoo_task_id_odoo_tasks",
            nullable=False,
        ),
        sa.Column("cycle_no", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("qa_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", _enum("outcome", "PASS", "REWORK", "RETEST"), nullable=True),
        _fk(
            "final_approved_by",
            "users.id",
            "fk_qa_cycles_final_approved_by_users",
            nullable=True,
        ),
        sa.Column("final_approved_at", sa.DateTime(timezone=True), nullable=True),
        _pk("qa_cycles"),
        sa.UniqueConstraint("odoo_task_id", "cycle_no", name="uq_qa_cycles_task_cycle"),
    )
    op.create_table(
        "requirement_sources",
        *_audit(),
        _fk(
            "qa_cycle_id",
            "qa_cycles.id",
            "fk_requirement_sources_qa_cycle_id_qa_cycles",
            nullable=False,
        ),
        sa.Column("kind", _enum("kind", "recording", "transcript"), nullable=False),
        sa.Column("file_path", sa.Unicode(1024), nullable=True),
        sa.Column("transcript_text", sa.UnicodeText(), nullable=True),
        _fk(
            "provided_by",
            "users.id",
            "fk_requirement_sources_provided_by_users",
            nullable=False,
        ),
        _pk("requirement_sources"),
    )
    op.create_table(
        "user_stories",
        *_audit(),
        _fk(
            "qa_cycle_id",
            "qa_cycles.id",
            "fk_user_stories_qa_cycle_id_qa_cycles",
            nullable=False,
        ),
        _fk(
            "template_id",
            "templates.id",
            "fk_user_stories_template_id_templates",
            nullable=False,
        ),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("status", _enum("status", "draft", "approved"), nullable=False),
        _pk("user_stories"),
    )
    op.create_table(
        "requirements",
        *_audit(),
        _fk(
            "qa_cycle_id",
            "qa_cycles.id",
            "fk_requirements_qa_cycle_id_qa_cycles",
            nullable=False,
        ),
        _fk(
            "template_id",
            "templates.id",
            "fk_requirements_template_id_templates",
            nullable=False,
        ),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("status", _enum("status", "draft", "approved"), nullable=False),
        _pk("requirements"),
    )
    op.create_table(
        "master_test_cases",
        *_audit(),
        _fk(
            "module_id",
            "modules.id",
            "fk_master_test_cases_module_id_modules",
            nullable=False,
        ),
        sa.Column("functional_area", sa.Unicode(200), nullable=False),
        sa.Column("case_no", sa.String(64), nullable=False),
        sa.Column("title", sa.Unicode(500), nullable=False),
        sa.Column("steps", sa.JSON(), nullable=False),
        sa.Column("expected_result", sa.UnicodeText(), nullable=False),
        sa.Column("priority", sa.Unicode(32), nullable=True),
        sa.Column("type", sa.Unicode(64), nullable=True),
        sa.Column("status", _enum("status", "active", "retired"), nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("source", _enum("source", "ai", "human"), nullable=False),
        _pk("master_test_cases"),
        sa.UniqueConstraint("module_id", "case_no", name="uq_master_test_cases_module_case_no"),
    )
    op.create_table(
        "master_test_case_versions",
        *_audit(),
        _fk(
            "master_test_case_id",
            "master_test_cases.id",
            "fk_master_test_case_versions_master_test_case_id_master_test_cases",
            nullable=False,
        ),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        _fk(
            "changed_by",
            "users.id",
            "fk_master_test_case_versions_changed_by_users",
            nullable=False,
        ),
        sa.Column("reason", sa.UnicodeText(), nullable=False),
        _pk("master_test_case_versions"),
        sa.UniqueConstraint(
            "master_test_case_id",
            "version_no",
            name="uq_master_test_case_versions_case_version",
        ),
    )
    op.create_table(
        "task_test_sets",
        *_audit(),
        _fk(
            "qa_cycle_id",
            "qa_cycles.id",
            "fk_task_test_sets_qa_cycle_id_qa_cycles",
            nullable=False,
        ),
        sa.Column(
            "status",
            _enum("status", "draft", "in_review", "approved", "sent"),
            nullable=False,
        ),
        _pk("task_test_sets"),
    )
    op.create_table(
        "task_test_set_items",
        *_audit(),
        _fk(
            "set_id",
            "task_test_sets.id",
            "fk_task_test_set_items_set_id_task_test_sets",
            nullable=False,
        ),
        _fk(
            "master_case_id",
            "master_test_cases.id",
            "fk_task_test_set_items_master_case_id_master_test_cases",
            nullable=True,
        ),
        sa.Column("proposed_case", sa.JSON(), nullable=False),
        sa.Column(
            "origin",
            _enum("origin", "master_regression", "ai_new", "manual_new"),
            nullable=False,
        ),
        sa.Column(
            "review_decision",
            _enum("review_decision", "pending", "approved", "modified", "removed"),
            nullable=False,
        ),
        sa.Column("decision_reason", sa.UnicodeText(), nullable=True),
        _fk(
            "reviewed_by",
            "users.id",
            "fk_task_test_set_items_reviewed_by_users",
            nullable=True,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_seconds", sa.Integer(), nullable=True),
        sa.Column("diff", sa.JSON(), nullable=True),
        _pk("task_test_set_items"),
    )
    op.create_table(
        "executions",
        *_audit(),
        _fk(
            "qa_cycle_id",
            "qa_cycles.id",
            "fk_executions_qa_cycle_id_qa_cycles",
            nullable=False,
        ),
        _fk("set_id", "task_test_sets.id", "fk_executions_set_id_task_test_sets", nullable=False),
        sa.Column("executor", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        _pk("executions"),
    )
    op.create_table(
        "execution_results",
        *_audit(),
        _fk(
            "execution_id",
            "executions.id",
            "fk_execution_results_execution_id_executions",
            nullable=False,
        ),
        _fk(
            "item_id",
            "task_test_set_items.id",
            "fk_execution_results_item_id_task_test_set_items",
            nullable=False,
        ),
        sa.Column(
            "ai_result",
            _enum("ai_result", "PASSED", "FAILED", "BLOCKED", "ERROR"),
            nullable=False,
        ),
        sa.Column("actual_behaviour", sa.UnicodeText(), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=True),
        _pk("execution_results"),
        sa.UniqueConstraint("execution_id", "item_id", name="uq_execution_results_execution_item"),
    )
    op.create_table(
        "result_validations",
        *_audit(),
        _fk(
            "result_id",
            "execution_results.id",
            "fk_result_validations_result_id_execution_results",
            nullable=False,
        ),
        sa.Column("tester_result", sa.String(32), nullable=False),
        sa.Column("decision", _enum("decision", "confirmed", "overridden"), nullable=False),
        sa.Column("reproduced_manually", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.UnicodeText(), nullable=True),
        _fk(
            "validated_by",
            "users.id",
            "fk_result_validations_validated_by_users",
            nullable=False,
        ),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        _pk("result_validations"),
        sa.UniqueConstraint("result_id", name="uq_result_validations_result_id"),
    )
    op.create_table(
        "reports",
        *_audit(),
        _fk("qa_cycle_id", "qa_cycles.id", "fk_reports_qa_cycle_id_qa_cycles", nullable=False),
        sa.Column("type", _enum("type", "task", "master"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("file_path", sa.Unicode(1024), nullable=False),
        sa.Column("odoo_attachment_id", sa.String(64), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        _pk("reports"),
        sa.UniqueConstraint(
            "qa_cycle_id",
            "type",
            "version",
            name="uq_reports_cycle_type_version",
        ),
    )
    op.create_table(
        "review_flags",
        *_audit(),
        sa.Column("rule_code", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.BigInteger(), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        _pk("review_flags"),
    )
    op.create_table(
        "audit_log",
        *_audit(),
        sa.Column("actor", sa.String(320), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("entity", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=False),
        sa.Column("before", sa.JSON(), nullable=True),
        sa.Column("after", sa.JSON(), nullable=True),
        _pk("audit_log"),
    )
    op.create_table(
        "jobs",
        *_audit(),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            _enum("status", "pending", "running", "succeeded", "failed"),
            nullable=False,
        ),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("locked_by", sa.String(128), nullable=True),
        sa.Column("last_error", sa.UnicodeText(), nullable=True),
        _pk("jobs"),
    )

    _created_by_indexes()
    _single_column_indexes()
    op.create_index("ix_odoo_tasks_stage_deadline", "odoo_tasks", ["odoo_stage", "deadline"])
    op.create_index("ix_audit_log_entity", "audit_log", ["entity", "entity_id"])
    op.create_index("ix_jobs_status_run_at", "jobs", ["status", "run_at"])
    op.create_index("ix_review_flags_entity", "review_flags", ["entity_type", "entity_id"])
    op.create_index(
        "uq_templates_one_active_per_type",
        "templates",
        ["type"],
        unique=True,
        mssql_where=sa.text("is_active = 1"),
    )
    _created_by_foreign_keys()
    op.bulk_insert(
        sa.table("roles", sa.column("code", sa.String(32))),
        [{"code": code} for code in _ROLE_CODES],
    )


def _single_column_indexes() -> None:
    indexes = {
        "users": ("role_id",),
        "api_keys": ("user_id",),
        "odoo_tasks": ("module_id", "assigned_tester_id"),
        "qa_cycles": ("odoo_task_id", "final_approved_by"),
        "requirement_sources": ("qa_cycle_id", "provided_by"),
        "user_stories": ("qa_cycle_id", "template_id"),
        "requirements": ("qa_cycle_id", "template_id"),
        "master_test_cases": ("module_id",),
        "master_test_case_versions": ("master_test_case_id", "changed_by"),
        "task_test_sets": ("qa_cycle_id",),
        "task_test_set_items": ("set_id", "master_case_id", "reviewed_by"),
        "executions": ("qa_cycle_id", "set_id"),
        "execution_results": ("execution_id", "item_id"),
        "result_validations": ("result_id", "validated_by"),
        "reports": ("qa_cycle_id",),
        "review_flags": ("resolved",),
    }
    for table, columns in indexes.items():
        for column in columns:
            op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade() -> None:
    for table in _DROP_BEFORE_USERS:
        op.drop_table(table)
    op.drop_constraint("fk_roles_created_by_users", "roles", type_="foreignkey")
    op.drop_constraint("fk_users_created_by_users", "users", type_="foreignkey")
    op.drop_table("users")
    op.drop_table("roles")
