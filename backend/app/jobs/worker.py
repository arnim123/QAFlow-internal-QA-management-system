"""Idle worker. Same image as the API. No jobs are registered yet."""

import logging
import signal
import time

from app.core.config import get_settings
from app.core.logging import setup_logging

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
    logger.info(
        "worker idle; no jobs registered",
        extra={"sleep_seconds": settings.worker_sleep_seconds},
    )

    while not stop:
        time.sleep(1)


if __name__ == "__main__":
    main()
