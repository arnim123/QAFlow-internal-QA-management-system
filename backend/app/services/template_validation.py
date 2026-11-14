"""JSON Schema checks for template documents and the templates themselves."""

import re

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError
from pydantic import ValidationError as PydanticValidationError

from app.schemas.templates import ColumnSpec, FieldError

_REQUIRED = re.compile(r"'([^']+)' is a required property")
_QUOTED = re.compile(r"'([^']+)'")


class TemplateRejected(Exception):
    """A template definition or a payload does not match the rules."""

    def __init__(
        self,
        message: str,
        errors: list[FieldError],
        status_code: int = 422,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.errors = errors
        self.status_code = status_code


def field_errors(schema: dict[str, object], payload: object) -> list[FieldError]:
    """Return one error per JSON Schema failure. An empty list means the payload matches."""

    validator = Draft202012Validator(schema)
    found = [
        FieldError(field=_field_name(error), message=error.message)
        for error in validator.iter_errors(payload)
    ]
    found.sort(key=lambda item: (item.field, item.message))
    unique: list[FieldError] = []
    seen: set[tuple[str, str]] = set()
    for error in found:
        key = (error.field, error.message)
        if key in seen:
            continue
        seen.add(key)
        unique.append(error)
    return unique


def schema_field_errors(schema: object) -> list[FieldError]:
    """Reject anything that is not a Draft 2020-12 schema for an object document."""

    if not isinstance(schema, dict):
        return [FieldError(field="json_schema", message="Schema must be a JSON object")]
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        message = exc.message if len(exc.message) <= 500 else f"{exc.message[:500]}…"
        return [FieldError(field=_schema_field(exc), message=message)]
    if schema.get("type") != "object":
        return [
            FieldError(
                field="json_schema.type",
                message="The root schema type must be object",
            )
        ]
    return []


def column_field_errors(columns: object) -> list[FieldError]:
    if not isinstance(columns, list) or len(columns) == 0:
        return [FieldError(field="columns", message="Add at least one display column")]
    errors: list[FieldError] = []
    for index, item in enumerate(columns):
        try:
            ColumnSpec.model_validate(item)
        except PydanticValidationError as exc:
            errors.extend(_column_errors(index, exc))
    return errors


def _column_errors(index: int, exc: PydanticValidationError) -> list[FieldError]:
    errors: list[FieldError] = []
    for item in exc.errors():
        parts = [part for part in item["loc"]]
        suffix = _join(parts)
        field = f"columns[{index}]" if suffix == "(root)" else f"columns[{index}].{suffix}"
        errors.append(FieldError(field=field, message=str(item["msg"])))
    return errors


def _schema_field(exc: SchemaError) -> str:
    path = _join(list(exc.absolute_path))
    if path == "(root)":
        return "json_schema"
    return f"json_schema.{path}"


def _field_name(error: ValidationError) -> str:
    path = _join(list(error.absolute_path))
    if error.validator == "required":
        match = _REQUIRED.search(error.message)
        if match:
            return _append(path, match.group(1))
    if error.validator == "additionalProperties":
        names = _QUOTED.findall(error.message)
        if len(names) == 1:
            return _append(path, names[0])
    return path


def _append(path: str, name: str) -> str:
    if path == "(root)":
        return name
    return f"{path}.{name}"


def _join(parts: list[object]) -> str:
    rendered = ""
    for part in parts:
        if isinstance(part, int):
            rendered += f"[{part}]"
        elif rendered == "":
            rendered = str(part)
        else:
            rendered += f".{part}"
    return rendered or "(root)"
