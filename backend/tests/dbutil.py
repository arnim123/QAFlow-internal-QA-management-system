"""SQL Server setup shared by foundation tests. Skips when the server is unreachable."""

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE = "qaflow_test"


def recreate_database(source: URL) -> None:
    admin = engine(source.set(database="master"), autocommit=True)
    try:
        with admin.connect() as connection:
            exists = connection.execute(
                text("SELECT DB_ID(:name)"),
                {"name": TEST_DATABASE},
            ).scalar()
            if exists is not None:
                connection.execute(
                    text(
                        f"ALTER DATABASE [{TEST_DATABASE}] "
                        "SET SINGLE_USER WITH ROLLBACK IMMEDIATE"
                    )
                )
                connection.execute(text(f"DROP DATABASE [{TEST_DATABASE}]"))
            connection.execute(text(f"CREATE DATABASE [{TEST_DATABASE}]"))
    finally:
        admin.dispose()


def engine(url: URL, *, autocommit: bool = False) -> Engine:
    options: dict[str, object] = {
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 10,
        "connect_args": {"timeout": 5},
    }
    if autocommit:
        options["isolation_level"] = "AUTOCOMMIT"
    return create_engine(url, **options)


def alembic(method: str, revision: str) -> None:
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    previous = Path.cwd()
    os.chdir(BACKEND_ROOT)
    try:
        getattr(command, method)(cfg, revision)
    finally:
        os.chdir(previous)


def session_factory(bind: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=bind, autoflush=False, autocommit=False)


def test_database_url() -> URL:
    from app.core.config import get_settings

    source = make_url(os.environ.get("DATABASE_URL") or get_settings().database_url)
    return source
