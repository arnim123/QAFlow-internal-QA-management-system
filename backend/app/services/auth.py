"""Email and password sign-in, and the principal carried by a session cookie."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    SignInNotConfigured,
    TokenError,
    decode_user_id,
    dummy_password_hash,
    encode_user_token,
    verify_password,
)
from app.models.enums import RoleCode
from app.models.identity import Role, User
from app.services.errors import AuthFailed, Unavailable


@dataclass(frozen=True)
class Principal:
    user_id: int
    email: str
    display_name: str
    role: RoleCode
    actor: str
    api_key_id: int | None = None

    @property
    def created_by(self) -> int:
        return self.user_id


def authenticate_password(session: Session, email: str, password: str) -> tuple[User, RoleCode]:
    """Return the user when the password matches an active human account."""

    user = session.scalar(select(User).where(User.email == email.strip()))
    password_hash = user.password_hash if user is not None else None
    if not password_hash:
        verify_password(password, dummy_password_hash())
        raise AuthFailed("Invalid credentials")
    if not verify_password(password, password_hash):
        raise AuthFailed("Invalid credentials")
    if user is None or not user.is_active:
        raise AuthFailed("Invalid credentials")
    role = session.get(Role, user.role_id)
    if role is None or role.code == RoleCode.executor_bot:
        raise AuthFailed("Invalid credentials")
    return user, role.code


def issue_token(user: User) -> str:
    try:
        return encode_user_token(user.id)
    except SignInNotConfigured as exc:
        raise Unavailable("Sign-in is not configured") from exc


def principal_from_cookie(session: Session, token: str) -> Principal:
    try:
        user_id = decode_user_id(token)
    except TokenError as exc:
        raise AuthFailed("Invalid credentials") from exc
    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthFailed("Invalid credentials")
    role = session.get(Role, user.role_id)
    if role is None:
        raise AuthFailed("Invalid credentials")
    return Principal(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=role.code,
        actor=user.email,
    )
