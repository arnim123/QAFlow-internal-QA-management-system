"""Worker process. Claims jobs with a SQL Server row lock and runs registered handlers."""

import logging
import os
import signal
import socket
import time
from collections.abc import Callable

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.core.logging import setup_logging
from app.services.jobs import process_next

logger = logging.getLogger(__name__)


def main() -> None:
    setup_logging()
    settings = get_settings()
    stop = False

    def request_stop(signum: int, _frame: object) -> None:
        nonlocal stop
        stop = True
        logger.info("worker stopping", extra={"signal": signum})

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    worker_id = f"{socket.gethostname()}:{os.getpid()}"
    logger.info(
        "worker started",
        extra={"worker_id": worker_id, "sleep_seconds": settings.worker_sleep_seconds},
    )

    while not stop:
        session = get_session_factory()()
        worked = False
        try:
            worked = process_next(session, worker_id)
        except Exception:
            logger.exception("worker iteration failed")
        finally:
            session.close()
        if not worked and not stop:
            _wait(lambda: stop, settings.worker_sleep_seconds)


def _wait(should_stop: Callable[[], bool], seconds: float) -> None:
    deadline = time.monotonic() + seconds
    while not should_stop() and time.monotonic() < deadline:
        time.sleep(min(1.0, deadline - time.monotonic()))


if __name__ == "__main__":
    main()
