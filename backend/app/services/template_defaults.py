"""Seeded document formats. Version 1 of each template type.

Changing a format after it is stored is a new template version, not an edit
of these values. The company's existing spreadsheet is still unknown
(`docs/OPEN_QUESTIONS.md`).
"""

import copy
from dataclasses import dataclass
from typing import Any

from app.models.enums import TemplateType

_SCHEMA = "https://json-schema.org/draft/2020-12/schema"


@dataclass(frozen=True)
class TemplateSeed:
    template_type: TemplateType
    json_schema: dict[str, Any]
    columns: list[dict[str, Any]]


def _string(description: str, *, min_length: int | None = 1) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "string", "description": description}
    if min_length is not None:
        schema["minLength"] = min_length
    return schema


def _integer(description: str, *, minimum: int) -> dict[str, Any]:
    return {"type": "integer", "minimum": minimum, "description": description}


def _object(
    properties: dict[str, Any],
    required: list[str],
    *,
    description: str | None = None,
) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": required,
    }
    if description:
        schema["description"] = description
    return schema


def _document(
    properties: dict[str, Any],
    required: list[str],
    *,
    description: str,
) -> dict[str, Any]:
    schema = _object(properties, required, description=description)
    schema["$schema"] = _SCHEMA
    return schema


def _string_array(description: str, *, min_items: int | None = None) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "type": "array",
        "description": description,
        "items": {"type": "string", "minLength": 1},
    }
    if min_items:
        schema["minItems"] = min_items
    return schema


def _columns(*rows: tuple[str, str, str | None]) -> list[dict[str, Any]]:
    return [{"key": key, "label": label, "section": section} for key, label, section in rows]


_STEPS = {
    "type": "array",
    "description": "Actions and the expected outcome of each one",
    "minItems": 1,
    "items": _object(
        {
            "action": _string("What the tester or executor does"),
            "expected": _string("What should be true after the action"),
        },
        ["action", "expected"],
    ),
}

_TOTALS = _object(
    {
        "total": _integer("Cases in the cycle", minimum=0),
        "passed": _integer("Passed results", minimum=0),
        "failed": _integer("Failed results", minimum=0),
        "blocked": _integer("Blocked results", minimum=0),
        "error": _integer("Error results", minimum=0),
    },
    ["total", "passed", "failed", "blocked", "error"],
    description="Result totals",
)

_SEEDS: tuple[TemplateSeed, ...] = (
    TemplateSeed(
        template_type=TemplateType.user_story,
        json_schema=_document(
            {
                "title": _string("Short name of the story"),
                "as_a": _string("The person who wants the change"),
                "i_want": _string("What that person wants to do"),
                "so_that": _string("Why the change matters"),
                "acceptance_criteria": _string_array(
                    "Conditions that show the story is met",
                    min_items=1,
                ),
            },
            ["title", "as_a", "i_want", "so_that", "acceptance_criteria"],
            description="A user story drafted from the transcript and the task.",
        ),
        columns=_columns(
            ("title", "Title", None),
            ("as_a", "As a", None),
            ("i_want", "I want", None),
            ("so_that", "So that", None),
            ("acceptance_criteria", "Acceptance criteria", None),
        ),
    ),
    TemplateSeed(
        template_type=TemplateType.requirement,
        json_schema=_document(
            {
                "id": _string("Requirement identifier, such as FR-1"),
                "description": _string("What the change must do"),
                "expected_behaviour": _string("What a person can observe when this is met"),
            },
            ["id", "description", "expected_behaviour"],
            description="A functional requirement and the behaviour the change must show.",
        ),
        columns=_columns(
            ("id", "Id", None),
            ("description", "Description", None),
            ("expected_behaviour", "Expected behaviour", None),
        ),
    ),
    TemplateSeed(
        template_type=TemplateType.test_case,
        json_schema=_document(
            {
                "case_no": _string("Case number, unique inside the module"),
                "title": _string("Short name of the case"),
                "functional_area": _string("Area of the module this case covers"),
                "type": _string("Kind of case. The SOP does not fix this vocabulary."),
                "priority": _string("Priority label. The SOP does not fix this vocabulary."),
                "preconditions": _string("State required before the first step", min_length=None),
                "steps": _STEPS,
                "expected_result": _string("Outcome the case as a whole must show"),
                "test_data": _string("Data the case needs", min_length=None),
            },
            [
                "case_no",
                "title",
                "functional_area",
                "type",
                "priority",
                "preconditions",
                "steps",
                "expected_result",
                "test_data",
            ],
            description="A test case with steps, an expected result, and the data it needs.",
        ),
        columns=_columns(
            ("case_no", "Case no", None),
            ("title", "Title", None),
            ("functional_area", "Functional area", None),
            ("type", "Type", None),
            ("priority", "Priority", None),
            ("preconditions", "Preconditions", None),
            ("steps", "Steps", None),
            ("expected_result", "Expected result", None),
            ("test_data", "Test data", None),
        ),
    ),
    TemplateSeed(
        template_type=TemplateType.execution_result,
        json_schema=_document(
            {
                "case_no": _string("Case number this result belongs to"),
                "result": {
                    "type": "string",
                    "description": "AI result. It stays an AI result until a tester confirms it.",
                    "enum": ["PASSED", "FAILED", "BLOCKED", "ERROR"],
                },
                "actual_behaviour": _string("What actually happened"),
                "evidence": _string_array("Paths or notes that show what happened"),
                "notes": _string("Extra notes from the executor", min_length=None),
            },
            ["case_no", "result", "actual_behaviour", "evidence"],
            description="A GrokBot result for one approved case.",
        ),
        columns=_columns(
            ("case_no", "Case no", None),
            ("result", "Result", None),
            ("actual_behaviour", "Actual behaviour", None),
            ("evidence", "Evidence", None),
            ("notes", "Notes", None),
        ),
    ),
    TemplateSeed(
        template_type=TemplateType.report,
        json_schema=_document(
            {
                "summary": _object(
                    {
                        "task": _string("Odoo task name"),
                        "module": _string("Module under test"),
                        "cycle_number": _integer("QA cycle number", minimum=1),
                        "tester": _string("Tester who owns the cycle"),
                        "dates": _string("Start and end of the cycle"),
                        "totals": _TOTALS,
                    },
                    ["task", "module", "cycle_number", "tester", "dates", "totals"],
                    description="Cycle summary",
                ),
                "test_cases": {
                    "type": "array",
                    "description": "Cases used for this task",
                    "items": {"type": "object"},
                },
                "ai_execution_results": {
                    "type": "array",
                    "description": "AI execution results for this cycle",
                    "items": {"type": "object"},
                },
                "manual_observations": _string(
                    "What the tester observed while validating results",
                    min_length=None,
                ),
                "final_status": _string("Final status of the cycle"),
            },
            [
                "summary",
                "test_cases",
                "ai_execution_results",
                "manual_observations",
                "final_status",
            ],
            description=(
                "A task-wise testing report. Columns are the Excel sections; "
                "the schema is the document that is validated."
            ),
        ),
        columns=_columns(
            ("task", "Task", "Summary"),
            ("module", "Module", "Summary"),
            ("cycle_number", "Cycle number", "Summary"),
            ("tester", "Tester", "Summary"),
            ("dates", "Dates", "Summary"),
            ("total", "Total", "Summary"),
            ("passed", "Passed", "Summary"),
            ("failed", "Failed", "Summary"),
            ("blocked", "Blocked", "Summary"),
            ("error", "Error", "Summary"),
            ("case_no", "Case no", "Test cases"),
            ("title", "Title", "Test cases"),
            ("expected_result", "Expected result", "Test cases"),
            ("case_no", "Case no", "AI execution results"),
            ("result", "Result", "AI execution results"),
            ("actual_behaviour", "Actual behaviour", "AI execution results"),
            ("notes", "Notes", "Manual QA observations"),
            ("final_status", "Final status", "Final status"),
        ),
    ),
)


def default_templates() -> tuple[TemplateSeed, ...]:
    """Return a copy of every seeded template."""

    return tuple(
        TemplateSeed(
            template_type=seed.template_type,
            json_schema=copy.deepcopy(seed.json_schema),
            columns=copy.deepcopy(seed.columns),
        )
        for seed in _SEEDS
    )


def default_for(template_type: TemplateType) -> TemplateSeed:
    for seed in default_templates():
        if seed.template_type is template_type:
            return seed
    raise KeyError(template_type)
