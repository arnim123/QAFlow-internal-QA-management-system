"""Liveness does not touch the database. Readiness checks SQL Server."""

import logging

from sqlalchemy import text

from app.core.database import get_engine
from app.schemas.health import HealthResponse, ReadyResponse

logger = logging.getLogger(__name__)


def liveness() -> HealthResponse:
    return HealthResponse(status="ok")


def readiness() -> ReadyResponse:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        logger.warning("readiness database check failed", exc_info=True)
        return ReadyResponse(status="unavailable", database="unavailable")
    return ReadyResponse(status="ok", database="ok")
