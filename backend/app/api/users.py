"""Admin user create and list."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import abort, require
from app.core.database import get_db
from app.core.permissions import Permission
from app.schemas.users import UserCreate, UserOut
from app.services.auth import Principal
from app.services.errors import ServiceError
from app.services.users import UserView, create_user, list_users

router = APIRouter(tags=["users"])


@router.get("/users", response_model=list[UserOut])
def get_users(
    session: Session = Depends(get_db),
    _principal: Principal = Depends(require(Permission.users_read)),
) -> list[UserOut]:
    return [_out(user) for user in list_users(session)]


@router.post("/users", response_model=UserOut, status_code=201)
def post_user(
    body: UserCreate,
    session: Session = Depends(get_db),
    principal: Principal = Depends(require(Permission.users_manage)),
) -> UserOut:
    try:
        created = create_user(
            session,
            actor=principal.actor,
            created_by=principal.created_by,
            email=body.email,
            display_name=body.display_name,
            role=body.role,
            password=body.password,
        )
    except ServiceError as exc:
        abort(exc)
    session.commit()
    return _out(created)


def _out(user: UserView) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        is_active=user.is_active,
    )
