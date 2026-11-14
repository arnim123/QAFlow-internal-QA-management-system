"""Human accounts and the admin seeded from the environment."""

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import PasswordTooLong, hash_password
from app.models.enums import RoleCode
from app.models.identity import Role, User
from app.services.audit import audited
from app.services.errors import BadRequest, Conflict

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UserView:
    id: int
    email: str
    display_name: str
    role: RoleCode
    is_active: bool


def list_users(session: Session) -> list[UserView]:
    rows = session.execute(
        select(User, Role.code).join(Role, Role.id == User.role_id).order_by(User.id)
    )
    return [
        UserView(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            role=code,
            is_active=user.is_active,
        )
        for user, code in rows
    ]


@audited(action="user.create", entity="user")
def create_user(
    session: Session,
    *,
    actor: str,
    created_by: int | None,
    email: str,
    display_name: str,
    role: RoleCode,
    password: str | None,
) -> tuple[UserView, str, None, dict[str, object]]:
    """Create one account. executor_bot has no password. The password is not audited."""

    cleaned_email = email.strip()
    cleaned_name = display_name.strip()
    if not cleaned_email or not cleaned_name:
        raise BadRequest("Email and display name are required")
    role_row = session.scalar(select(Role).where(Role.code == role))
    if role_row is None:
        raise BadRequest("Unknown role")
    if session.scalar(select(User.id).where(User.email == cleaned_email)) is not None:
        raise Conflict("A user with this email already exists")
    try:
        password_hash = _password_hash_for(role, password)
    except PasswordTooLong as exc:
        raise BadRequest("Password must be at most 72 bytes") from exc
    user = User(
        email=cleaned_email,
        display_name=cleaned_name,
        role_id=role_row.id,
        password_hash=password_hash,
        is_active=True,
        created_by=created_by,
    )
    session.add(user)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise Conflict("A user with this email already exists") from exc
    view = UserView(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=role,
        is_active=True,
    )
    after = {
        "email": view.email,
        "display_name": view.display_name,
        "role": role.value,
        "is_active": True,
    }
    return view, str(view.id), None, after


def seed_admin(session: Session) -> bool:
    """Insert the admin from the environment when that email is not already present.

    A later boot does not reset the password. Empty admin env vars skip seeding.
    """

    settings = get_settings()
    email = settings.admin_email.strip()
    password = settings.admin_password
    if not email or not password:
        logger.info("admin seed skipped")
        return False
    existing = session.scalar(select(User).where(User.email == email))
    if existing is not None:
        logger.info("admin seed skipped; user exists")
        return False
    role = session.scalar(select(Role).where(Role.code == RoleCode.admin))
    if role is None:
        raise RuntimeError("admin role is not seeded")
    try:
        password_hash = hash_password(password)
    except PasswordTooLong as exc:
        raise RuntimeError("ADMIN_PASSWORD must be at most 72 bytes") from exc
    session.add(
        User(
            email=email,
            display_name=settings.admin_display_name.strip() or "Administrator",
            role_id=role.id,
            password_hash=password_hash,
            is_active=True,
        )
    )
    session.commit()
    logger.info("admin user seeded")
    return True


def _password_hash_for(role: RoleCode, password: str | None) -> str | None:
    if role == RoleCode.executor_bot:
        if password:
            raise BadRequest("executor_bot users do not have passwords")
        return None
    if not password:
        raise BadRequest("Password is required")
    return hash_password(password)
