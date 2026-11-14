"""Bearer keys for executor_bot. The plaintext is returned once and only the hash is stored."""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import generate_api_key, hash_api_key
from app.models.enums import RoleCode
from app.models.identity import ApiKey, Role, User
from app.services.audit import audited
from app.services.auth import Principal
from app.services.errors import AuthFailed, BadRequest, Conflict, NotFound


@dataclass(frozen=True)
class IssuedApiKey:
    id: int
    user_id: int
    name: str
    key_prefix: str
    token: str


@dataclass(frozen=True)
class ApiKeyView:
    id: int
    user_id: int
    name: str
    key_prefix: str
    revoked_at: datetime | None
    last_used_at: datetime | None


def list_api_keys(session: Session) -> list[ApiKeyView]:
    rows = session.scalars(select(ApiKey).order_by(ApiKey.id))
    return [_view(row) for row in rows]


@audited(action="api_key.create", entity="api_key")
def create_api_key(
    session: Session,
    *,
    actor: str,
    created_by: int | None,
    user_id: int,
    name: str,
) -> tuple[IssuedApiKey, str, None, dict[str, object]]:
    user = session.get(User, user_id)
    if user is None:
        raise NotFound("User not found")
    if not user.is_active:
        raise BadRequest("User is inactive")
    role = session.get(Role, user.role_id)
    if role is None or role.code != RoleCode.executor_bot:
        raise BadRequest("API keys can only be created for an executor_bot user")
    cleaned = name.strip()
    if not cleaned:
        raise BadRequest("Name is required")
    token, prefix, digest = generate_api_key()
    row = ApiKey(
        user_id=user.id,
        name=cleaned,
        key_hash=digest,
        key_prefix=prefix,
        created_by=created_by,
    )
    session.add(row)
    session.flush()
    issued = IssuedApiKey(
        id=row.id,
        user_id=row.user_id,
        name=row.name,
        key_prefix=row.key_prefix,
        token=token,
    )
    after = {"name": row.name, "key_prefix": prefix, "user_id": user.id}
    return issued, str(row.id), None, after


@audited(action="api_key.revoke", entity="api_key")
def revoke_api_key(
    session: Session,
    *,
    actor: str,
    created_by: int | None,
    key_id: int,
) -> tuple[ApiKeyView, str, dict[str, object], dict[str, object]]:
    row = session.get(ApiKey, key_id)
    if row is None:
        raise NotFound("API key not found")
    if row.revoked_at is not None:
        raise Conflict("API key is already revoked")
    row.revoked_at = datetime.now(UTC)
    session.flush()
    view = _view(row)
    return (
        view,
        str(row.id),
        {"revoked_at": None},
        {"revoked_at": row.revoked_at.isoformat()},
    )


def authenticate_api_key(session: Session, token: str) -> Principal:
    """Resolve a bearer key. Commits `last_used_at` so a later 403 still records the use."""

    row = session.scalar(select(ApiKey).where(ApiKey.key_hash == hash_api_key(token)))
    if row is None or row.revoked_at is not None:
        raise AuthFailed("Invalid credentials")
    user = session.get(User, row.user_id)
    if user is None or not user.is_active:
        raise AuthFailed("Invalid credentials")
    role = session.get(Role, user.role_id)
    if role is None or role.code != RoleCode.executor_bot:
        raise AuthFailed("Invalid credentials")
    principal = Principal(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=RoleCode.executor_bot,
        actor=f"api_key:{row.key_prefix}",
        api_key_id=row.id,
    )
    row.last_used_at = datetime.now(UTC)
    session.commit()
    return principal


def _view(row: ApiKey) -> ApiKeyView:
    return ApiKeyView(
        id=row.id,
        user_id=row.user_id,
        name=row.name,
        key_prefix=row.key_prefix,
        revoked_at=row.revoked_at,
        last_used_at=row.last_used_at,
    )
