"""Declarative base and the columns present on every table."""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Index, MetaData, text
from sqlalchemy.dialects.mssql import ROWVERSION
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column
from sqlalchemy.schema import FetchedValue

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def fk(target: str, name: str) -> ForeignKey:
    """Foreign key that does not cascade. History is not hard-deleted."""

    return ForeignKey(target, name=name, ondelete="NO ACTION")


def indexes(table: str, *columns: str) -> tuple[Index, ...]:
    return tuple(Index(f"ix_{table}_{column}", column) for column in columns)


class AuditMixin:
    """Identity, audit stamps, and a SQL Server rowversion."""

    @declared_attr
    def id(cls) -> Mapped[int]:
        return mapped_column(BigInteger, Identity(), primary_key=True, sort_order=-50)

    @declared_attr
    def created_at(cls) -> Mapped[datetime]:
        return mapped_column(
            DateTime(timezone=True),
            nullable=False,
            server_default=text("SYSDATETIMEOFFSET()"),
            sort_order=-40,
        )

    @declared_attr
    def updated_at(cls) -> Mapped[datetime]:
        return mapped_column(
            DateTime(timezone=True),
            nullable=False,
            server_default=text("SYSDATETIMEOFFSET()"),
            onupdate=text("SYSDATETIMEOFFSET()"),
            sort_order=-30,
        )

    @declared_attr
    def created_by(cls) -> Mapped[int | None]:
        return mapped_column(
            BigInteger,
            ForeignKey(
                "users.id",
                name=f"fk_{cls.__tablename__}_created_by_users",
                ondelete="NO ACTION",
                use_alter=True,
            ),
            nullable=True,
            sort_order=-20,
        )

    @declared_attr
    def row_version(cls) -> Mapped[bytes]:
        # ROWVERSION is server-generated on insert and update. FetchedValue
        # keeps it out of INSERT and UPDATE column lists.
        return mapped_column(
            ROWVERSION(),
            FetchedValue(),
            nullable=False,
            server_onupdate=FetchedValue(),
            sort_order=-10,
        )

    @declared_attr.directive
    def __mapper_args__(cls) -> dict[str, Any]:
        return {
            "version_id_col": cls.__table__.c.row_version,
            "version_id_generator": False,
            "eager_defaults": "auto",
        }
