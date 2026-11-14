"""Template routes. Business rules live in the template service."""

import json
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.catalog import Template
from app.models.enums import TemplateType
from app.schemas.templates import (
    ActorRequest,
    PreviewRequest,
    PreviewResponse,
    TemplateOut,
    TemplateWrite,
)
from app.services import acceptance
from app.services import templates as template_service
from app.services.template_validation import TemplateRejected


def template_rejected_handler(_request: Request, exc: TemplateRejected) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.message,
            "errors": [error.model_dump() for error in exc.errors],
        },
    )


def build_template_router() -> APIRouter:
    router = APIRouter(tags=["templates"])

    @router.get("/templates", response_model=list[TemplateOut])
    def list_templates(session: Session = Depends(get_db)) -> list[TemplateOut]:
        return [_serialize(row) for row in template_service.list_templates(session)]

    @router.get("/templates/{template_type}/active", response_model=TemplateOut)
    def active_template(
        template_type: TemplateType,
        session: Session = Depends(get_db),
    ) -> TemplateOut:
        return _serialize(template_service.get_active(session, template_type))

    @router.get(
        "/templates/{template_type}/versions/{version}",
        response_model=TemplateOut,
    )
    def template_version(
        template_type: TemplateType,
        version: int,
        session: Session = Depends(get_db),
    ) -> TemplateOut:
        return _serialize(template_service.get_version(session, template_type, version))

    @router.post(
        "/templates/{template_type}/versions",
        response_model=TemplateOut,
        status_code=201,
    )
    def create_template_version(
        template_type: TemplateType,
        body: TemplateWrite,
        session: Session = Depends(get_db),
    ) -> TemplateOut:
        row = template_service.create_version(
            session,
            template_type,
            body.json_schema,
            [column.model_dump() for column in body.columns],
            actor=body.actor,
            reason=body.reason,
            activate=body.activate,
        )
        session.commit()
        session.refresh(row)
        return _serialize(row)

    @router.post(
        "/templates/{template_type}/versions/{version}/activate",
        response_model=TemplateOut,
    )
    def activate_template_version(
        template_type: TemplateType,
        version: int,
        body: ActorRequest,
        session: Session = Depends(get_db),
    ) -> TemplateOut:
        row = template_service.activate_version(
            session,
            template_type,
            version,
            actor=body.actor,
            reason=body.reason,
        )
        session.commit()
        session.refresh(row)
        return _serialize(row)

    @router.post("/templates/{template_type}/preview", response_model=PreviewResponse)
    def preview_template(
        template_type: TemplateType,
        body: PreviewRequest,
        session: Session = Depends(get_db),
    ) -> PreviewResponse:
        acceptance.check_payload(session, template_type, body.payload, body.json_schema)
        return PreviewResponse(valid=True, errors=[])

    return router


def _serialize(row: Template) -> TemplateOut:
    return TemplateOut(
        id=row.id,
        type=row.template_type,
        version=row.version,
        is_active=row.is_active,
        json_schema=_json_object(row.json_schema),
        columns=_json_columns(row.columns),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _json_object(value: object) -> dict[str, Any]:
    parsed = _decode(value)
    if isinstance(parsed, dict):
        return parsed
    return {}


def _json_columns(value: object) -> list[dict[str, Any]]:
    parsed = _decode(value)
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, dict)]


def _decode(value: object) -> object:
    if isinstance(value, str):
        return json.loads(value)
    return value
