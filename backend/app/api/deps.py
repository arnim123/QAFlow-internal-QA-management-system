"""Authentication dependencies."""

from collections.abc import Callable
from typing import NoReturn

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import Permission, has_permission
from app.core.security import SESSION_COOKIE
from app.models.enums import RoleCode
from app.services.api_keys import authenticate_api_key
from app.services.auth import Principal, principal_from_cookie
from app.services.errors import AuthFailed, ServiceError


def abort(exc: ServiceError) -> NoReturn:
    raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


def get_current_principal(
    request: Request,
    session: Session = Depends(get_db),
) -> Principal:
    header = request.headers.get("authorization")
    if header is not None:
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            raise HTTPException(status_code=401, detail="Invalid credentials")
        try:
            return authenticate_api_key(session, token.strip())
        except AuthFailed as exc:
            abort(exc)
    cookie = request.cookies.get(SESSION_COOKIE)
    if not cookie:
        raise HTTPException(status_code=401, detail="Missing credentials")
    try:
        return principal_from_cookie(session, cookie)
    except AuthFailed as exc:
        abort(exc)


def require(*permissions: Permission) -> Callable[..., Principal]:
    def checker(principal: Principal = Depends(get_current_principal)) -> Principal:
        if any(not has_permission(principal.role, permission) for permission in permissions):
            raise HTTPException(status_code=403, detail="Forbidden")
        return principal

    return checker


def require_human(principal: Principal = Depends(get_current_principal)) -> Principal:
    if principal.role == RoleCode.executor_bot:
        raise HTTPException(status_code=403, detail="Forbidden")
    return principal
