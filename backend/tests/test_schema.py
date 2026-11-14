"""Upgrade, insert one full QA cycle, then downgrade on SQL Server.

Skips when SQL Server is unreachable so image builds can run pytest without a database.
Point DATABASE_URL at the server. The test recreates the separate database qaflow_test.
"""

import json
import os
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text, true
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.models import (
    ApiKey,
    AuditLog,
    Execution,
    ExecutionResult,
    Job,
    MasterTestCase,
    MasterTestCaseVersion,
    Module,
    OdooTask,
    QaCycle,
    Report,
    Requirement,
    RequirementSource,
    ResultValidation,
    ReviewFlag,
    Role,
    Setting,
    TaskTestSet,
    TaskTestSetItem,
    Template,
    User,
    UserStory,
)
from app.models.enums import (
    AiResult,
    CaseSource,
    CycleOutcome,
    DraftStatus,
    ItemOrigin,
    JobStatus,
    MasterCaseStatus,
    ReportType,
    ReviewDecision,
    RoleCode,
    SetStatus,
    SourceKind,
    TemplateType,
    ValidationDecision,
)

BACKEND_ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE = "qaflow_test"
DOMAIN_TABLES = frozenset(
    {
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
    }
)


def test_domain_schema_happy_path() -> None:
    source = make_url(os.environ.get("DATABASE_URL") or get_settings().database_url)
    try:
        _recreate_database(source)
    except Exception as exc:
        pytest.skip(f"SQL Server connection failed: {exc}")

    test_url = source.set(database=TEST_DATABASE)
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = test_url.render_as_string(hide_password=False)
    get_settings.cache_clear()
    try:
        _alembic("upgrade", "head")
        _assert_templates_seeded(test_url)
        engine = _engine(test_url)
        try:
            _insert_happy_path(engine)
            _assert_rejects_duplicates(engine)
        finally:
            engine.dispose()
        _alembic("downgrade", "base")
        _assert_domain_tables_absent(test_url)
        _alembic("upgrade", "head")
        _assert_roles_seeded(test_url)
        _assert_templates_seeded(test_url)
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
        get_settings.cache_clear()


def _recreate_database(source: URL) -> None:
    admin = _engine(source.set(database="master"), autocommit=True)
    try:
        with admin.connect() as connection:
            exists = connection.execute(
                text("SELECT DB_ID(:name)"),
                {"name": TEST_DATABASE},
            ).scalar()
            if exists is not None:
                connection.execute(
                    text(
                        f"ALTER DATABASE [{TEST_DATABASE}] "
                        "SET SINGLE_USER WITH ROLLBACK IMMEDIATE"
                    )
                )
                connection.execute(text(f"DROP DATABASE [{TEST_DATABASE}]"))
            connection.execute(text(f"CREATE DATABASE [{TEST_DATABASE}]"))
    finally:
        admin.dispose()


def _engine(url: URL, *, autocommit: bool = False) -> Engine:
    options: dict[str, object] = {"pool_pre_ping": True, "connect_args": {"timeout": 5}}
    if autocommit:
        options["isolation_level"] = "AUTOCOMMIT"
    return create_engine(url, **options)


def _alembic(method: str, revision: str) -> None:
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    previous = Path.cwd()
    os.chdir(BACKEND_ROOT)
    try:
        getattr(command, method)(cfg, revision)
    finally:
        os.chdir(previous)


def _insert_happy_path(engine: Engine) -> None:
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    now = datetime.now(UTC)
    with session_factory() as session:
        roles = {role.code: role for role in session.scalars(select(Role))}
        assert set(roles) == set(RoleCode)

        admin = User(
            email="admin@example.com",
            display_name="Admin",
            role_id=roles[RoleCode.admin].id,
            is_active=True,
        )
        session.add(admin)
        session.flush()

        tester = _user(session, "tester@example.com", "Tester", roles[RoleCode.tester], admin)
        provider = _user(
            session,
            "provider@example.com",
            "Requirement provider",
            roles[RoleCode.requirement_provider],
            admin,
        )
        bot = _user(
            session,
            "grokbot@example.com",
            "GrokBot",
            roles[RoleCode.executor_bot],
            admin,
        )
        session.add(
            ApiKey(
                user_id=bot.id,
                name="GrokBot",
                key_hash="a" * 64,
                key_prefix="qf_test",
                created_by=admin.id,
            )
        )
        module = Module(
            name="Inventory",
            overview="Stock and transfers",
            functional_areas=["Transfers"],
            created_by=admin.id,
        )
        session.add(module)
        story_template = session.scalar(
            select(Template).where(
                Template.template_type == TemplateType.user_story,
                Template.is_active == true(),
            )
        )
        requirement_template = session.scalar(
            select(Template).where(
                Template.template_type == TemplateType.requirement,
                Template.is_active == true(),
            )
        )
        assert story_template is not None
        assert requirement_template is not None

        task = OdooTask(
            odoo_id=1001,
            name="Adjust stock transfer",
            module_id=module.id,
            priority="1",
            deadline=now,
            odoo_stage="Deployed on Beta and Pending For Testing",
            assigned_tester_id=tester.id,
            task_sub_status="Documentation Required",
            estimated_hours=Decimal("3.50"),
            actual_hours=Decimal("2.00"),
            qa_started=True,
            qa_passed=True,
            qa_cycles=0,
            description_hash="b" * 64,
            checklist=[{"text": "Verify the transfer", "done": False}],
            last_synced_at=now,
            raw={"id": 1001},
            created_by=admin.id,
        )
        session.add(task)
        session.flush()

        cycle = QaCycle(
            odoo_task_id=task.id,
            cycle_no=1,
            status="closed",
            qa_started_at=now,
            outcome=CycleOutcome.PASS,
            final_approved_by=tester.id,
            final_approved_at=now,
            created_by=tester.id,
        )
        session.add(cycle)
        session.flush()

        session.add(
            RequirementSource(
                qa_cycle_id=cycle.id,
                kind=SourceKind.transcript,
                file_path="recordings/transfer.txt",
                transcript_text="The transfer must keep the source quantity.",
                provided_by=provider.id,
                created_by=provider.id,
            )
        )
        session.add(
            UserStory(
                qa_cycle_id=cycle.id,
                template_id=story_template.id,
                content={"story": "As a clerk I transfer stock"},
                status=DraftStatus.approved,
                created_by=tester.id,
            )
        )
        session.add(
            Requirement(
                qa_cycle_id=cycle.id,
                template_id=requirement_template.id,
                content={"requirement": "Source quantity decreases"},
                status=DraftStatus.approved,
                created_by=tester.id,
            )
        )
        case = MasterTestCase(
            module_id=module.id,
            functional_area="Transfers",
            case_no="INV-001",
            title="Transfer reduces source quantity",
            steps=[{"action": "Confirm the transfer"}],
            expected_result="Source on-hand quantity decreases",
            priority="high",
            case_type="functional",
            status=MasterCaseStatus.active,
            current_version=1,
            source=CaseSource.human,
            created_by=tester.id,
        )
        session.add(case)
        session.flush()
        session.add(
            MasterTestCaseVersion(
                master_test_case_id=case.id,
                version_no=1,
                snapshot={"case_no": "INV-001", "title": case.title},
                changed_by=tester.id,
                reason="Approved for the master repository",
                created_by=tester.id,
            )
        )
        test_set = TaskTestSet(
            qa_cycle_id=cycle.id,
            status=SetStatus.sent,
            created_by=tester.id,
        )
        session.add(test_set)
        session.flush()
        item = TaskTestSetItem(
            set_id=test_set.id,
            master_case_id=case.id,
            proposed_case={"case_no": "INV-001"},
            origin=ItemOrigin.master_regression,
            review_decision=ReviewDecision.approved,
            decision_reason="Covers the transfer change",
            reviewed_by=tester.id,
            reviewed_at=now,
            review_seconds=120,
            diff=None,
            created_by=tester.id,
        )
        session.add(item)
        session.flush()
        execution = Execution(
            qa_cycle_id=cycle.id,
            set_id=test_set.id,
            executor="grokbot",
            status="finished",
            claimed_at=now,
            finished_at=now,
            raw_payload={"executor": "grokbot"},
            created_by=bot.id,
        )
        session.add(execution)
        session.flush()
        result = ExecutionResult(
            execution_id=execution.id,
            item_id=item.id,
            ai_result=AiResult.PASSED,
            actual_behaviour="Source quantity decreased",
            evidence={"note": "observed"},
            created_by=bot.id,
        )
        session.add(result)
        session.flush()
        session.add(
            ResultValidation(
                result_id=result.id,
                tester_result="PASSED",
                decision=ValidationDecision.confirmed,
                reproduced_manually=False,
                notes="Matches the expected transfer",
                validated_by=tester.id,
                validated_at=now,
                created_by=tester.id,
            )
        )
        session.add(
            Report(
                qa_cycle_id=cycle.id,
                report_type=ReportType.task,
                version=1,
                file_path="reports/task-1001-v1.xlsx",
                odoo_attachment_id="55",
                posted_at=now,
                created_by=tester.id,
            )
        )
        session.add(
            ReviewFlag(
                rule_code="fast_approval",
                entity_type="task_test_set",
                entity_id=test_set.id,
                severity="info",
                details={"review_seconds": 120},
                resolved=False,
                created_by=admin.id,
            )
        )
        session.add(
            AuditLog(
                actor="tester@example.com",
                action="approve_set",
                entity="task_test_set",
                entity_id=str(test_set.id),
                before={"status": "in_review"},
                after={"status": "sent"},
                created_by=tester.id,
            )
        )
        session.add(
            Job(
                job_type="odoo_writeback",
                payload={"odoo_id": 1001},
                status=JobStatus.pending,
                run_at=now,
                attempts=0,
                created_by=admin.id,
            )
        )
        session.add(
            Setting(
                key="odoo.field.qa_started",
                value="",
                created_by=admin.id,
            )
        )
        session.commit()

    with session_factory() as session:
        task = session.scalar(select(OdooTask).where(OdooTask.odoo_id == 1001))
        assert task is not None
        assert task.checklist == [{"text": "Verify the transfer", "done": False}]
        assert task.row_version
        assert len(task.row_version) == 8
        assert task.estimated_hours == Decimal("3.50")
        original_version = task.row_version
        task.name = "Adjust stock transfer (reviewed)"
        session.commit()
        session.refresh(task)
        assert task.row_version != original_version
        module = session.scalar(select(Module).where(Module.name == "Inventory"))
        assert module is not None
        assert module.functional_areas == ["Transfers"]
        cycle = session.scalar(select(QaCycle).where(QaCycle.odoo_task_id == task.id))
        assert cycle is not None
        assert cycle.outcome == CycleOutcome.PASS
        story = session.scalar(select(UserStory).where(UserStory.qa_cycle_id == cycle.id))
        assert story is not None
        assert story.content == {"story": "As a clerk I transfer stock"}
        assert story.status == DraftStatus.approved
        for model in (
            ApiKey,
            RequirementSource,
            Requirement,
            MasterTestCase,
            MasterTestCaseVersion,
            TaskTestSet,
            TaskTestSetItem,
            Execution,
            ExecutionResult,
            ResultValidation,
            Report,
            ReviewFlag,
            AuditLog,
            Job,
            Setting,
            Template,
            User,
            Role,
        ):
            assert session.scalar(select(model.id)) is not None
        checks = set(
            session.scalars(text("SELECT name FROM sys.check_constraints")).all()
        )
        assert "ck_roles_code" in checks
        assert "ck_qa_cycles_outcome" in checks


def _user(session: Session, email: str, name: str, role: Role, admin: User) -> User:
    user = User(
        email=email,
        display_name=name,
        role_id=role.id,
        is_active=True,
        created_by=admin.id,
    )
    session.add(user)
    session.flush()
    return user


def _assert_templates_seeded(url: URL) -> None:
    engine = _engine(url)
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text("SELECT [type], version, is_active, json_schema FROM templates")
            ).all()
    finally:
        engine.dispose()
    active = {row[0] for row in rows if row[2]}
    assert active == {member.value for member in TemplateType}
    schemas = {}
    for row in rows:
        if row[1] != 1:
            continue
        schema = row[3]
        if isinstance(schema, str):
            schema = json.loads(schema)
        schemas[row[0]] = schema
    assert schemas["user_story"]["properties"]["as_a"]["type"] == "string"
    assert set(schemas["execution_result"]["properties"]["result"]["enum"]) == {
        "PASSED",
        "FAILED",
        "BLOCKED",
        "ERROR",
    }


def _assert_rejects_duplicates(engine: Engine) -> None:
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with session_factory() as session:
        module = session.scalar(select(Module).where(Module.name == "Inventory"))
        assert module is not None
        with pytest.raises(IntegrityError):
            session.add(OdooTask(odoo_id=1001, name="Duplicate task"))
            session.commit()
        session.rollback()
        with pytest.raises(IntegrityError):
            session.add(
                MasterTestCase(
                    module_id=module.id,
                    functional_area="Transfers",
                    case_no="INV-001",
                    title="Duplicate",
                    steps=[],
                    expected_result="Duplicate",
                    status=MasterCaseStatus.active,
                    current_version=1,
                    source=CaseSource.human,
                )
            )
            session.commit()
        session.rollback()


def _assert_domain_tables_absent(url: URL) -> None:
    engine = _engine(url)
    try:
        with engine.connect() as connection:
            present = set(
                connection.execute(
                    text(
                        "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
                        "WHERE TABLE_SCHEMA = 'dbo'"
                    )
                ).scalars()
            )
    finally:
        engine.dispose()
    assert present.isdisjoint(DOMAIN_TABLES)


def _assert_roles_seeded(url: URL) -> None:
    engine = _engine(url)
    try:
        with engine.connect() as connection:
            codes = set(connection.execute(text("SELECT code FROM roles")).scalars())
    finally:
        engine.dispose()
    assert codes == {role.value for role in RoleCode}
