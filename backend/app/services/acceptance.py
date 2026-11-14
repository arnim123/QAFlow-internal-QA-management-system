"""The only gate for AI drafts and GrokBot results.

SOP R1 and R4: passing validation does not approve a draft and does not
confirm an AI result. These functions do not write user stories, requirements,
or execution results. Callers that store those records call here first.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.models.enums import TemplateType
from app.schemas.templates import FieldError
from app.services.template_validation import TemplateRejected, field_errors, schema_field_errors
from app.services.templates import coerce_template_type, validate

_AI_DRAFTS = frozenset(
    {
        TemplateType.user_story,
        TemplateType.requirement,
        TemplateType.test_case,
        TemplateType.report,
    }
)


def accept_ai_output(
    session: Session,
    template_type: TemplateType | str,
    payload: object,
) -> dict[str, Any]:
    """Accept a user story, requirement, test case, or report draft."""

    parsed = coerce_template_type(template_type)
    if parsed not in _AI_DRAFTS:
        raise TemplateRejected(
            "GrokBot results use the execution result template",
            [
                FieldError(
                    field="type",
                    message="Use accept_execution_result for GrokBot results",
                )
            ],
        )
    return validate(session, parsed, payload)


def accept_execution_result(session: Session, payload: object) -> dict[str, Any]:
    """Accept one GrokBot result. It is still an AI result after this check."""

    return validate(session, TemplateType.execution_result, payload)


def check_payload(
    session: Session,
    template_type: TemplateType | str,
    payload: object,
    json_schema: dict[str, Any] | None = None,
) -> None:
    """Validate against the active template, or against a schema that is not saved yet."""

    parsed = coerce_template_type(template_type)
    if json_schema is None:
        if parsed is TemplateType.execution_result:
            accept_execution_result(session, payload)
        else:
            accept_ai_output(session, parsed, payload)
        return
    problems = schema_field_errors(json_schema)
    if problems:
        raise TemplateRejected("Template schema is not valid", problems)
    problems = field_errors(json_schema, payload)
    if problems:
        raise TemplateRejected("Payload does not match the template", problems)
