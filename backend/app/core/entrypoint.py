"""API process: wait for SQL Server, migrate, then serve."""

import logging
import sys
import time
from pathlib import Path

import uvicorn
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import ensure_database, get_engine
from app.core.logging import setup_logging

logger = logging.getLogger(__name__)

_WAIT_ATTEMPTS = 90
_WAIT_DELAY_SECONDS = 2.0
_BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _alembic_config() -> Config:
    return Config(str(_BACKEND_ROOT / "alembic.ini"))


def wait_for_database() -> None:
    last_error: Exception | None = None
    for attempt in range(1, _WAIT_ATTEMPTS + 1):
        try:
            ensure_database()
            with get_engine().connect() as connection:
                connection.execute(text("SELECT 1"))
            logger.info("database ready", extra={"attempt": attempt})
            return
        except Exception as exc:
            last_error = exc
            logger.warning(
                "database not ready",
                extra={"attempt": attempt, "error": type(exc).__name__},
            )
            time.sleep(_WAIT_DELAY_SECONDS)
    raise RuntimeError("SQL Server did not become ready") from last_error


def migrate() -> None:
    logger.info("running migrations")
    command.upgrade(_alembic_config(), "head")


def serve(reload: bool) -> None:
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=reload,
        log_config=None,
    )


def main() -> None:
    setup_logging()
    wait_for_database()
    migrate()
    serve(reload="--reload" in sys.argv)


if __name__ == "__main__":
    main()
