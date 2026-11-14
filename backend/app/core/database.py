"""SQL Server engine and sessions."""

import re
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Create the engine on first use so imports do not load pyodbc."""

    global _engine
    if _engine is None:
        _engine = create_engine(get_settings().database_url, pool_pre_ping=True)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    return _session_factory


def get_db() -> Generator[Session]:
    session = get_session_factory()()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def dispose_engine() -> None:
    """Drop the cached engine so a new DATABASE_URL is picked up."""

    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None


def _query_value(url: URL, key: str) -> str | None:
    value = url.query.get(key)
    if value is None:
        return None
    if isinstance(value, list | tuple):
        return str(value[-1])
    return str(value)


def odbc_connect_string(database: str) -> str:
    """Build an ODBC string for `database` from DATABASE_URL."""

    url = make_url(get_settings().database_url)
    driver = _query_value(url, "driver") or "ODBC Driver 18 for SQL Server"
    parts = [
        f"DRIVER={{{driver}}}",
        f"SERVER={url.host},{url.port or 1433}",
        f"DATABASE={database}",
        f"UID={url.username or ''}",
        f"PWD={url.password or ''}",
    ]
    for key in ("TrustServerCertificate", "Encrypt"):
        value = _query_value(url, key)
        if value is not None:
            parts.append(f"{key}={value}")
    return ";".join(parts)


def ensure_database() -> None:
    """Create the configured database when it is missing. No other DDL."""

    import pyodbc

    url = make_url(get_settings().database_url)
    target = url.database
    if not target or target.lower() == "master":
        return
    if not _IDENTIFIER.fullmatch(target):
        raise ValueError("Refusing to create a database with an unsafe name")

    connection = pyodbc.connect(odbc_connect_string("master"), autocommit=True)
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT DB_ID(?)", target)
        row = cursor.fetchone()
        if row is not None and row[0] is not None:
            return
        cursor.execute(f"CREATE DATABASE [{target}]")
    finally:
        connection.close()
