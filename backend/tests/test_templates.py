"""Template validation, and versioning that leaves the previous row unchanged."""

import copy
import os
from collections.abc import Generator
from pathlib import Path
from typing import cast

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text, true
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.database import dispose_engine
from app.main import create_app
from app.models import AuditLog, Template
from app.models.enums import TemplateType
from app.services.acceptance import accept_ai_output
from app.services.template_defaults import default_for
from app.services.template_validation import (
    TemplateRejected,
    column_field_errors,
    field_errors,
    schema_field_errors,
)

BACKEND_ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE = "qaflow_template_test"

SAMPLES: dict[TemplateType, dict[str, object]] = {
    TemplateType.user_story: {
        "title": "Transfer stock",
        "as_a": "warehouse clerk",
        "i_want": "to confirm a transfer",
        "so_that": "the source quantity stays correct",
        "acceptance_criteria": ["Source on-hand decreases by the transferred amount"],
    },
    TemplateType.requirement: {
        "id": "FR-1",
        "description": "Source quantity decreases when a transfer is confirmed",
        "expected_behaviour": "The source location on-hand quantity is reduced",
    },
    TemplateType.test_case: {
        "case_no": "INV-001",
        "title": "Transfer reduces source quantity",
        "functional_area": "Transfers",
        "type": "functional",
        "priority": "high",
        "preconditions": "The source location has stock",
        "steps": [{"action": "Confirm the transfer", "expected": "The transfer is done"}],
        "expected_result": "Source on-hand quantity decreases",
        "test_data": "Product A, quantity 2",
    },
    TemplateType.execution_result: {
        "case_no": "INV-001",
        "result": "PASSED",
        "actual_behaviour": "Source quantity decreased by 2",
        "evidence": ["screen-transfer.png"],
        "notes": "Observed on beta",
    },
    TemplateType.report: {
        "summary": {
            "task": "Adjust stock transfer",
            "module": "Inventory",
            "cycle_number": 1,
            "tester": "Ada",
            "dates": "2026-11-14",
            "totals": {"total": 1, "passed": 1, "failed": 0, "blocked": 0, "error": 0},
        },
        "test_cases": [{"case_no": "INV-001"}],
        "ai_execution_results": [{"case_no": "INV-001", "result": "PASSED"}],
        "manual_observations": "Checked the source quantity.",
        "final_status": "Pass",
    },
}


@pytest.mark.parametrize("template_type", list(TemplateType))
def test_default_sample_matches_its_schema(template_type: TemplateType) -> None:
    seed = default_for(template_type)
    assert schema_field_errors(seed.json_schema) == []
    assert field_errors(seed.json_schema, SAMPLES[template_type]) == []


def test_missing_fields_are_named() -> None:
    errors = field_errors(default_for(TemplateType.requirement).json_schema, {})
    assert {error.field for error in errors} == {"id", "description", "expected_behaviour"}


def test_unknown_property_is_named() -> None:
    payload = dict(SAMPLES[TemplateType.user_story])
    payload["owner"] = "Ada"
    errors = field_errors(default_for(TemplateType.user_story).json_schema, payload)
    assert [error.field for error in errors] == ["owner"]


def test_step_errors_use_the_nested_field() -> None:
    payload = dict(SAMPLES[TemplateType.test_case])
    payload["steps"] = [{"action": "Confirm the transfer"}]
    errors = field_errors(default_for(TemplateType.test_case).json_schema, payload)
    assert any(error.field == "steps[0].expected" for error in errors)


def test_execution_result_rejects_unknown_result_value() -> None:
    payload = dict(SAMPLES[TemplateType.execution_result])
    payload["result"] = "Passed"
    errors = field_errors(default_for(TemplateType.execution_result).json_schema, payload)
    assert [error.field for error in errors] == ["result"]
    assert "PASSED" in errors[0].message


def test_evidence_must_be_a_list() -> None:
    payload = dict(SAMPLES[TemplateType.execution_result])
    payload["evidence"] = "screen-transfer.png"
    errors = field_errors(default_for(TemplateType.execution_result).json_schema, payload)
    assert [error.field for error in errors] == ["evidence"]


def test_report_names_a_missing_summary_field() -> None:
    payload = copy.deepcopy(SAMPLES[TemplateType.report])
    summary = payload["summary"]
    assert isinstance(summary, dict)
    del summary["task"]
    errors = field_errors(default_for(TemplateType.report).json_schema, payload)
    assert any(error.field == "summary.task" for error in errors)


def test_schema_root_must_be_an_object() -> None:
    errors = schema_field_errors({"type": "string"})
    assert errors[0].field == "json_schema.type"


def test_column_errors_name_the_row() -> None:
    errors = column_field_errors([{"key": "title", "label": ""}])
    assert errors[0].field == "columns[0].label"


def test_ai_acceptance_rejects_execution_results() -> None:
    with pytest.raises(TemplateRejected) as caught:
        accept_ai_output(cast(Session, None), TemplateType.execution_result, {})
    assert caught.value.status_code == 422
    assert caught.value.errors[0].field == "type"


def test_unknown_template_type_is_rejected() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/templates/not-a-type/active")
    assert response.status_code == 422


@pytest.fixture(scope="module")
def template_api() -> Generator[tuple[TestClient, sessionmaker[Session]]]:
    source = make_url(os.environ.get("DATABASE_URL") or get_settings().database_url)
    try:
        _recreate_database(source)
    except Exception as exc:
        pytest.skip(f"SQL Server connection failed: {exc}")

    test_url = source.set(database=TEST_DATABASE)
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = test_url.render_as_string(hide_password=False)
    get_settings.cache_clear()
    dispose_engine()
    engine = _engine(test_url)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        _alembic("upgrade", "head")
        with TestClient(create_app()) as client:
            yield client, factory
    finally:
        engine.dispose()
        dispose_engine()
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
        get_settings.cache_clear()


def test_preview_rejects_invalid_results_and_accepts_valid_ones(
    template_api: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _factory = template_api
    invalid = client.post(
        "/templates/execution_result/preview",
        json={
            "payload": {
                "case_no": "INV-001",
                "result": "NOPE",
                "actual_behaviour": "Nothing happened",
                "evidence": [],
            }
        },
    )
    assert invalid.status_code == 422
    body = invalid.json()
    assert body["detail"] == "Payload does not match the template"
    assert any(error["field"] == "result" for error in body["errors"])

    valid = client.post(
        "/api/templates/execution_result/preview",
        json={"payload": SAMPLES[TemplateType.execution_result]},
    )
    assert valid.status_code == 200
    assert valid.json() == {"valid": True, "errors": []}


def test_new_version_does_not_change_the_previous_row(
    template_api: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, factory = template_api
    active = client.get("/templates/user_story/active")
    assert active.status_code == 200
    original = active.json()
    assert original["version"] == 1
    assert original["is_active"] is True
    original_id = original["id"]

    with factory() as session:
        stored = session.get(Template, original_id)
        assert stored is not None
        before = {
            "schema": copy.deepcopy(stored.json_schema),
            "columns": copy.deepcopy(stored.columns),
            "version": stored.version,
            "is_active": stored.is_active,
            "updated_at": stored.updated_at,
            "row_version": bytes(stored.row_version),
        }

    new_schema = copy.deepcopy(original["json_schema"])
    new_schema["properties"]["notes"] = {"type": "string", "minLength": 1}
    new_schema["required"] = [*new_schema["required"], "notes"]
    new_columns = copy.deepcopy(original["columns"])
    new_columns[0]["label"] = "Story title"

    created = client.post(
        "/templates/user_story/versions",
        json={
            "json_schema": new_schema,
            "columns": new_columns,
            "activate": False,
            "actor": "Ada",
            "reason": "Add notes",
        },
    )
    assert created.status_code == 201
    created_body = created.json()
    assert created_body["id"] != original_id
    assert created_body["version"] == 2
    assert created_body["is_active"] is False

    with factory() as session:
        stored = session.get(Template, original_id)
        assert stored is not None
        assert stored.json_schema == before["schema"]
        assert stored.columns == before["columns"]
        assert stored.version == before["version"]
        assert stored.is_active is True
        assert stored.updated_at == before["updated_at"]
        assert bytes(stored.row_version) == before["row_version"]

    activated = client.post(
        "/templates/user_story/versions/2/activate",
        json={"actor": "Ada", "reason": "Publish notes"},
    )
    assert activated.status_code == 200
    assert activated.json()["is_active"] is True

    with factory() as session:
        stored = session.get(Template, original_id)
        assert stored is not None
        assert stored.json_schema == before["schema"]
        assert stored.columns == before["columns"]
        assert stored.version == 1
        assert stored.is_active is False
        current = list(
            session.scalars(
                select(Template).where(
                    Template.template_type == TemplateType.user_story,
                    Template.is_active == true(),
                )
            )
        )
        assert len(current) == 1
        assert current[0].id == created_body["id"]
        assert current[0].json_schema["properties"]["notes"]["type"] == "string"
        assert current[0].columns[0]["label"] == "Story title"
        for template_type in TemplateType:
            if template_type is TemplateType.user_story:
                continue
            others = list(
                session.scalars(
                    select(Template).where(
                        Template.template_type == template_type,
                        Template.is_active == true(),
                    )
                )
            )
            assert len(others) == 1
            assert others[0].version == 1
        audit_created = session.scalar(
            select(AuditLog).where(
                AuditLog.action == "template_version_created",
                AuditLog.entity == "template",
                AuditLog.entity_id == str(created_body["id"]),
            )
        )
        assert audit_created is not None
        assert audit_created.actor == "Ada"
        assert audit_created.after is not None
        assert audit_created.after["version"] == 2
        assert audit_created.after["reason"] == "Add notes"
        audit_deactivated = session.scalar(
            select(AuditLog).where(
                AuditLog.action == "template_deactivated",
                AuditLog.entity_id == str(original_id),
            )
        )
        assert audit_deactivated is not None
        assert audit_deactivated.before == {
            "type": "user_story",
            "version": 1,
            "is_active": True,
        }
        assert audit_deactivated.after is not None
        assert audit_deactivated.after["is_active"] is False

    preserved = client.get("/templates/user_story/versions/1")
    assert preserved.status_code == 200
    assert preserved.json()["json_schema"] == before["schema"]
    assert preserved.json()["columns"] == before["columns"]
    active_now = client.get("/api/templates/user_story/active")
    assert active_now.status_code == 200
    assert active_now.json()["version"] == 2

    stale = client.post(
        "/templates/user_story/preview",
        json={"payload": SAMPLES[TemplateType.user_story]},
    )
    assert stale.status_code == 422
    assert any(error["field"] == "notes" for error in stale.json()["errors"])
    assert field_errors(before["schema"], SAMPLES[TemplateType.user_story]) == []

    rejected = client.post(
        "/templates/user_story/versions",
        json={
            "json_schema": {"type": "string"},
            "columns": new_columns,
            "actor": "Ada",
        },
    )
    assert rejected.status_code == 422
    assert rejected.json()["errors"][0]["field"] == "json_schema.type"
    with factory() as session:
        versions = session.scalars(
            select(Template.version).where(Template.template_type == TemplateType.user_story)
        ).all()
    assert sorted(versions) == [1, 2]

    missing = client.get("/templates/user_story/versions/99")
    assert missing.status_code == 404


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
