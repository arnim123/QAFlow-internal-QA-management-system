"""Create, list, and revoke executor API keys."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import abort, require
from app.core.database import get_db
from app.core.permissions import Permission
from app.schemas.api_keys import ApiKeyCreate, ApiKeyCreated, ApiKeyOut
from app.services.api_keys import (
    ApiKeyView,
    IssuedApiKey,
    create_api_key,
    list_api_keys,
    revoke_api_key,
)
from app.services.auth import Principal
from app.services.errors import ServiceError

router = APIRouter(tags=["api-keys"])


@router.get("/api-keys", response_model=list[ApiKeyOut])
def get_api_keys(
    session: Session = Depends(get_db),
    _principal: Principal = Depends(require(Permission.api_keys_manage)),
) -> list[ApiKeyOut]:
    return [_out(row) for row in list_api_keys(session)]


@router.post("/api-keys", response_model=ApiKeyCreated, status_code=201)
def post_api_key(
    body: ApiKeyCreate,
    session: Session = Depends(get_db),
    principal: Principal = Depends(require(Permission.api_keys_manage)),
) -> ApiKeyCreated:
    try:
        issued = create_api_key(
            session,
            actor=principal.actor,
            created_by=principal.created_by,
            user_id=body.user_id,
            name=body.name,
        )
    except ServiceError as exc:
        abort(exc)
    session.commit()
    return _created(issued)


@router.post("/api-keys/{key_id}/revoke", response_model=ApiKeyOut)
def post_revoke_api_key(
    key_id: int,
    session: Session = Depends(get_db),
    principal: Principal = Depends(require(Permission.api_keys_manage)),
) -> ApiKeyOut:
    try:
        revoked = revoke_api_key(
            session,
            actor=principal.actor,
            created_by=principal.created_by,
            key_id=key_id,
        )
    except ServiceError as exc:
        abort(exc)
    session.commit()
    return _out(revoked)


def _out(row: ApiKeyView) -> ApiKeyOut:
    return ApiKeyOut(
        id=row.id,
        user_id=row.user_id,
        name=row.name,
        key_prefix=row.key_prefix,
        revoked_at=row.revoked_at,
        last_used_at=row.last_used_at,
    )


def _created(row: IssuedApiKey) -> ApiKeyCreated:
    return ApiKeyCreated(
        id=row.id,
        user_id=row.user_id,
        name=row.name,
        key_prefix=row.key_prefix,
        token=row.token,
    )
