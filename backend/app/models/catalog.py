"""Modules, document templates, and admin settings."""

from sqlalchemy import JSON, Boolean, Integer, String, Unicode, UnicodeText, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import Index

from app.models.base import AuditMixin, Base, indexes
from app.models.enums import TemplateType, sa_enum


class Module(AuditMixin, Base):
    __tablename__ = "modules"
    __table_args__ = (
        UniqueConstraint("name", name="uq_modules_name"),
        *indexes("modules", "created_by"),
    )

    name: Mapped[str] = mapped_column(Unicode(200), nullable=False)
    overview: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    functional_areas: Mapped[list] = mapped_column(JSON, nullable=False)


class Template(AuditMixin, Base):
    __tablename__ = "templates"
    __table_args__ = (
        UniqueConstraint("type", "version", name="uq_templates_type_version"),
        Index(
            "uq_templates_one_active_per_type",
            "type",
            unique=True,
            mssql_where=text("is_active = 1"),
        ),
        *indexes("templates", "created_by"),
    )

    template_type: Mapped[TemplateType] = mapped_column(
        "type",
        sa_enum(TemplateType, "type"),
        nullable=False,
    )
    json_schema: Mapped[dict] = mapped_column(JSON, nullable=False)
    columns: Mapped[list] = mapped_column(JSON, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("0"),
    )


class Setting(AuditMixin, Base):
    __tablename__ = "settings"
    __table_args__ = (
        UniqueConstraint("key", name="uq_settings_key"),
        *indexes("settings", "created_by"),
    )

    key: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[str] = mapped_column(UnicodeText, nullable=False)
