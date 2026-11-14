"""Request and response models for document templates."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import TemplateType


class FieldError(BaseModel):
    field: str
    message: str


class ColumnSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    key: str = Field(min_length=1)
    label: str = Field(min_length=1)
    section: str | None = None

    @field_validator("section")
    @classmethod
    def blank_section(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class ActorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    actor: str = Field(min_length=1, max_length=320)
    reason: str | None = Field(default=None, max_length=2000)

    @field_validator("reason")
    @classmethod
    def blank_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class TemplateWrite(ActorRequest):
    json_schema: dict[str, Any]
    columns: list[ColumnSpec] = Field(min_length=1)
    activate: bool = True


class PreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload: Any
    json_schema: dict[str, Any] | None = None


class PreviewResponse(BaseModel):
    valid: bool = True
    errors: list[FieldError] = Field(default_factory=list)


class TemplateOut(BaseModel):
    id: int
    type: TemplateType
    version: int
    is_active: bool
    json_schema: dict[str, Any]
    columns: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime
