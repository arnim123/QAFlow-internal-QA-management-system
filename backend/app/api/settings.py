"""Read and update allowlisted settings. Secrets are not accepted."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import abort, require
from app.core.database import get_db
from app.core.permissions import Permission
from app.schemas.settings import SettingOut, SettingUpdate
from app.services.auth import Principal
from app.services.errors import ServiceError
from app.services.settings import SettingView, list_settings, set_setting

router = APIRouter(tags=["settings"])


@router.get("/settings", response_model=list[SettingOut])
def get_settings_route(
    session: Session = Depends(get_db),
    _principal: Principal = Depends(require(Permission.settings_read)),
) -> list[SettingOut]:
    return [_out(row) for row in list_settings(session)]


@router.put("/settings/{key}", response_model=SettingOut)
def put_setting(
    key: str,
    body: SettingUpdate,
    session: Session = Depends(get_db),
    principal: Principal = Depends(require(Permission.settings_write)),
) -> SettingOut:
    try:
        saved = set_setting(
            session,
            actor=principal.actor,
            created_by=principal.created_by,
            key=key,
            value=body.value,
        )
    except ServiceError as exc:
        abort(exc)
    session.commit()
    return _out(saved)


def _out(row: SettingView) -> SettingOut:
    return SettingOut(
        key=row.key,
        value=row.value,
        value_type=row.value_type,
        source=row.source,
    )
