"""Read-only audit log."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require
from app.core.database import get_db
from app.core.permissions import Permission
from app.models.ops import AuditLog
from app.schemas.audit import AuditOut
from app.services.audit import list_audit
from app.services.auth import Principal

router = APIRouter(tags=["audit"])


@router.get("/audit-log", response_model=list[AuditOut])
def get_audit_log(
    session: Session = Depends(get_db),
    _principal: Principal = Depends(require(Permission.audit_read)),
    entity: str | None = None,
    entity_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[AuditOut]:
    rows = list_audit(
        session,
        entity=entity,
        entity_id=entity_id,
        limit=limit,
        offset=offset,
    )
    return [_out(row) for row in rows]


def _out(row: AuditLog) -> AuditOut:
    return AuditOut(
        id=row.id,
        actor=row.actor,
        action=row.action,
        entity=row.entity,
        entity_id=row.entity_id,
        before=_copy(row.before),
        after=_copy(row.after),
        created_at=row.created_at,
    )


def _copy(value: dict[str, Any] | None) -> dict[str, Any] | None:
    if value is None:
        return None
    return dict(value)
