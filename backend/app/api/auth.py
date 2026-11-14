"""Email and password login. The session is a JWT in an httpOnly cookie."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import abort, require_human
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import SESSION_COOKIE
from app.schemas.auth import LoginIn, MeOut
from app.services.auth import Principal, authenticate_password, issue_token
from app.services.errors import ServiceError

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=MeOut)
def login(body: LoginIn, response: Response, session: Session = Depends(get_db)) -> MeOut:
    try:
        user, role = authenticate_password(session, body.email, body.password)
        token = issue_token(user)
    except ServiceError as exc:
        abort(exc)
    response.set_cookie(**_cookie_params(token))
    return MeOut(id=user.id, email=user.email, display_name=user.display_name, role=role)


@router.post("/auth/logout", status_code=204)
def logout(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        SESSION_COOKIE,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.app_env != "local",
    )


@router.get("/me", response_model=MeOut)
def me(principal: Principal = Depends(require_human)) -> MeOut:
    return MeOut(
        id=principal.user_id,
        email=principal.email,
        display_name=principal.display_name,
        role=principal.role,
    )


def _cookie_params(token: str) -> dict[str, object]:
    settings = get_settings()
    return {
        "key": SESSION_COOKIE,
        "value": token,
        "httponly": True,
        "secure": settings.app_env != "local",
        "samesite": "lax",
        "path": "/",
        "max_age": settings.jwt_expire_minutes * 60,
    }
