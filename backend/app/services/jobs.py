"""SQL Server job queue. Claim uses a row lock so two workers cannot take the same job."""

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.enums import JobStatus
from app.models.ops import Job
from app.services.audit import audited
from app.services.errors import Conflict, NotFound

logger = logging.getLogger(__name__)

Handler = Callable[[dict[str, Any]], None]
HANDLERS: dict[str, Handler] = {}

_CLAIM_SQL = """
SELECT TOP 1 id
FROM jobs WITH (UPDLOCK, READPAST, ROWLOCK)
WHERE status = :status
  AND (run_at IS NULL OR run_at <= SYSDATETIMEOFFSET())
ORDER BY run_at, id
"""
_ERROR_LIMIT = 4000


def enqueue(
    session: Session,
    *,
    job_type: str,
    payload: dict[str, Any],
    run_at: datetime | None = None,
    created_by: int | None = None,
) -> Job:
    job = Job(
        job_type=job_type,
        payload=payload,
        status=JobStatus.pending,
        run_at=run_at,
        attempts=0,
        created_by=created_by,
    )
    session.add(job)
    session.flush()
    return job


def claim(session: Session, worker_id: str) -> Job | None:
    """Lock one due job and mark it running. Commits so the lock is released."""

    row = session.execute(
        text(_CLAIM_SQL),
        {"status": JobStatus.pending.value},
    ).first()
    if row is None:
        session.rollback()
        return None
    job = session.get(Job, int(row[0]))
    if job is None:
        session.rollback()
        return None
    job.status = JobStatus.running
    job.locked_by = worker_id
    job.attempts = job.attempts + 1
    session.commit()
    return job


def complete(session: Session, job_id: int) -> Job:
    job = _require(session, job_id)
    job.status = JobStatus.succeeded
    job.locked_by = None
    session.commit()
    return job


def fail(session: Session, job_id: int, error: str) -> Job:
    """Record last_error. Requeue with exponential backoff until the attempt cap."""

    job = _require(session, job_id)
    settings = get_settings()
    job.last_error = _clip(error)
    job.locked_by = None
    if job.attempts < settings.job_max_attempts:
        job.status = JobStatus.pending
        job.run_at = datetime.now(UTC) + timedelta(seconds=backoff_seconds(job.attempts))
    else:
        job.status = JobStatus.failed
    session.commit()
    return job


def fail_terminal(session: Session, job_id: int, error: str) -> Job:
    """Fail once. Used when no handler is registered, so a typo does not retry."""

    job = _require(session, job_id)
    job.status = JobStatus.failed
    job.locked_by = None
    job.last_error = _clip(error)
    session.commit()
    return job


def backoff_seconds(attempts: int) -> float:
    settings = get_settings()
    exponent = max(attempts - 1, 0)
    delay = settings.job_backoff_base_seconds * (2**exponent)
    return min(delay, settings.job_backoff_max_seconds)


def list_jobs(session: Session, *, status: JobStatus | None = None) -> list[Job]:
    stmt = select(Job).order_by(Job.id.desc())
    if status is not None:
        stmt = stmt.where(Job.status == status)
    return list(session.scalars(stmt.limit(200)))


@audited(action="job.retry", entity="job")
def retry_job(
    session: Session,
    *,
    actor: str,
    created_by: int | None,
    job_id: int,
) -> tuple[Job, str, dict[str, object], dict[str, object]]:
    job = session.get(Job, job_id)
    if job is None:
        raise NotFound("Job not found")
    if job.status != JobStatus.failed:
        raise Conflict("Only a failed job can be retried")
    before = {
        "status": job.status.value,
        "attempts": job.attempts,
        "locked_by": job.locked_by,
    }
    job.status = JobStatus.pending
    job.run_at = datetime.now(UTC)
    job.attempts = 0
    job.locked_by = None
    session.flush()
    after = {"status": JobStatus.pending.value, "attempts": 0, "locked_by": None}
    return job, str(job.id), before, after


def dispatch(session: Session, job: Job) -> None:
    session.refresh(job)
    handler = HANDLERS.get(job.job_type)
    if handler is None:
        fail_terminal(session, job.id, f"no handler registered for {job.job_type}")
        return
    try:
        handler(dict(job.payload))
    except Exception as exc:
        logger.exception("job failed", extra={"job_id": job.id, "job_type": job.job_type})
        fail(session, job.id, str(exc))
    else:
        complete(session, job.id)


def process_next(session: Session, worker_id: str) -> bool:
    """Claim and run one job. Returns False when the queue has nothing due."""

    job = claim(session, worker_id)
    if job is None:
        return False
    dispatch(session, job)
    return True


def _require(session: Session, job_id: int) -> Job:
    job = session.get(Job, job_id)
    if job is None:
        raise NotFound("Job not found")
    return job


def _clip(error: str) -> str:
    if len(error) <= _ERROR_LIMIT:
        return error
    return error[:_ERROR_LIMIT]
