"""Users, the six role codes, and hashed API keys."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Unicode, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, Base, fk, indexes
from app.models.enums import RoleCode, sa_enum


class Role(AuditMixin, Base):
    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("code", name="uq_roles_code"),
        *indexes("roles", "created_by"),
    )

    code: Mapped[RoleCode] = mapped_column(sa_enum(RoleCode, "code"), nullable=False)


class User(AuditMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        *indexes("users", "role_id", "created_by"),
    )

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    display_name: Mapped[str] = mapped_column(Unicode(200), nullable=False)
    role_id: Mapped[int] = mapped_column(
        fk("roles.id", "fk_users_role_id_roles"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
    )
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)


class ApiKey(AuditMixin, Base):
    """Machine credential. Only the hash is stored."""

    __tablename__ = "api_keys"
    __table_args__ = (
        UniqueConstraint("key_hash", name="uq_api_keys_key_hash"),
        *indexes("api_keys", "user_id", "created_by"),
    )

    user_id: Mapped[int] = mapped_column(
        fk("users.id", "fk_api_keys_user_id_users"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Unicode(200), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(32), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
