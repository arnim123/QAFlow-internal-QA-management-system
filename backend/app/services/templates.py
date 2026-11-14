"""Document templates. A change inserts a new version and leaves the old row alone."""

import copy
from typing import Any

from sqlalchemy import func, select, true
from sqlalchemy.orm import Session

from app.models.catalog import Template
from app.models.enums import TemplateType
from app.schemas.templates import ColumnSpec, FieldError
from app.services.template_validation import (
    TemplateRejected,
    column_field_errors,
    field_errors,
    schema_field_errors,
)
from app.services.workflow import record_state_change


def validate(
    session: Session,
    template_type: TemplateType | str,
    payload: object,
) -> dict[str, Any]:
    """Check a payload against the one active template of this type.

    A payload that passes is still a draft or an AI result. This does not approve it.
    """

    template = get_active(session, template_type)
    schema = template.json_schema
    if not isinstance(schema, dict):
        raise TemplateRejected(
            "The active template schema is not an object",
            [FieldError(field="json_schema", message="Active schema is not a JSON object")],
        )
    problems = field_errors(schema, payload)
    if problems or not isinstance(payload, dict):
        if not problems:
            problems = [FieldError(field="(root)", message="Payload must be an object")]
        raise TemplateRejected("Payload does not match the template", problems)
    return payload


def list_templates(session: Session) -> list[Template]:
    return list(
        session.scalars(select(Template).order_by(Template.template_type, Template.version.desc()))
    )


def get_active(session: Session, template_type: TemplateType | str) -> Template:
    parsed = coerce_template_type(template_type)
    row = session.scalar(
        select(Template).where(
            Template.template_type == parsed,
            Template.is_active == true(),
        )
    )
    if row is None:
        raise TemplateRejected(
            "No active template for this type",
            [FieldError(field="type", message=f"No active {parsed.value} template")],
            status_code=404,
        )
    return row


def get_version(session: Session, template_type: TemplateType | str, version: int) -> Template:
    parsed = coerce_template_type(template_type)
    row = session.scalar(
        select(Template).where(
            Template.template_type == parsed,
            Template.version == version,
        )
    )
    if row is None:
        raise TemplateRejected(
            "Template version not found",
            [FieldError(field="version", message=f"Version {version} does not exist")],
            status_code=404,
        )
    return row


def create_version(
    session: Session,
    template_type: TemplateType | str,
    json_schema: object,
    columns: object,
    *,
    actor: str,
    reason: str | None = None,
    created_by: int | None = None,
    activate: bool = True,
) -> Template:
    """Insert the next version. The previous row's schema and columns are not written."""

    parsed = coerce_template_type(template_type)
    actor_name = actor.strip()
    if not actor_name:
        raise TemplateRejected(
            "Actor is required",
            [FieldError(field="actor", message="Enter who is making this change")],
        )
    problems = schema_field_errors(json_schema) + column_field_errors(columns)
    if problems:
        raise TemplateRejected("Template definition is invalid", problems)
    assert isinstance(json_schema, dict)
    assert isinstance(columns, list)
    stored_columns = [ColumnSpec.model_validate(item).model_dump() for item in columns]
    current = session.scalar(
        select(func.max(Template.version)).where(Template.template_type == parsed)
    )
    has_active = (
        session.scalar(
            select(Template.id).where(
                Template.template_type == parsed,
                Template.is_active == true(),
            )
        )
        is not None
    )
    row = Template(
        template_type=parsed,
        json_schema=copy.deepcopy(json_schema),
        columns=copy.deepcopy(stored_columns),
        version=int(current or 0) + 1,
        is_active=bool(activate and not has_active),
        created_by=created_by,
    )
    session.add(row)
    session.flush()
    record_state_change(
        session=session,
        entity="template",
        entity_id=str(row.id),
        action="template_version_created",
        actor=actor_name,
        reason=_reason(reason),
        created_by=created_by,
        after={
            "type": parsed.value,
            "version": row.version,
            "is_active": row.is_active,
        },
    )
    if activate and has_active:
        return activate_version(
            session,
            parsed,
            row.version,
            actor=actor_name,
            reason=reason,
            created_by=created_by,
        )
    return row


def activate_version(
    session: Session,
    template_type: TemplateType | str,
    version: int,
    *,
    actor: str,
    reason: str | None = None,
    created_by: int | None = None,
) -> Template:
    """Make one stored version active. Its schema and columns stay as they were."""

    parsed = coerce_template_type(template_type)
    actor_name = actor.strip()
    if not actor_name:
        raise TemplateRejected(
            "Actor is required",
            [FieldError(field="actor", message="Enter who is making this change")],
        )
    target = get_version(session, parsed, version)
    if target.is_active:
        return target
    previous = session.scalar(
        select(Template).where(
            Template.template_type == parsed,
            Template.is_active == true(),
        )
    )
    cleaned_reason = _reason(reason)
    if previous is not None and previous.id != target.id:
        previous.is_active = False
        session.flush()
        record_state_change(
            session=session,
            entity="template",
            entity_id=str(previous.id),
            action="template_deactivated",
            actor=actor_name,
            reason=cleaned_reason,
            created_by=created_by,
            before={
                "type": parsed.value,
                "version": previous.version,
                "is_active": True,
            },
            after={
                "type": parsed.value,
                "version": previous.version,
                "is_active": False,
            },
        )
    target.is_active = True
    session.flush()
    record_state_change(
        session=session,
        entity="template",
        entity_id=str(target.id),
        action="template_activated",
        actor=actor_name,
        reason=cleaned_reason,
        created_by=created_by,
        before={"type": parsed.value, "version": target.version, "is_active": False},
        after={"type": parsed.value, "version": target.version, "is_active": True},
    )
    return target


def coerce_template_type(value: TemplateType | str) -> TemplateType:
    if isinstance(value, TemplateType):
        return value
    try:
        return TemplateType(value)
    except ValueError as exc:
        raise TemplateRejected(
            "Unknown template type",
            [FieldError(field="type", message="Template type is not recognised")],
            status_code=404,
        ) from exc


def _reason(reason: str | None) -> str | None:
    if reason is None:
        return None
    stripped = reason.strip()
    return stripped or None
