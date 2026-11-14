"""Admin view of the job queue."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import abort, require
from app.core.database import get_db
from app.core.permissions import Permission
from app.models.enums import JobStatus
from app.models.ops import Job
from app.schemas.jobs import JobOut
from app.services.auth import Principal
from app.services.errors import ServiceError
from app.services.jobs import list_jobs, retry_job

router = APIRouter(tags=["jobs"])


@router.get("/jobs", response_model=list[JobOut])
def get_jobs(
    session: Session = Depends(get_db),
    _principal: Principal = Depends(require(Permission.jobs_read)),
    status: JobStatus | None = None,
) -> list[JobOut]:
    return [_out(job) for job in list_jobs(session, status=status)]


@router.post("/jobs/{job_id}/retry", response_model=JobOut)
def post_retry_job(
    job_id: int,
    session: Session = Depends(get_db),
    principal: Principal = Depends(require(Permission.jobs_retry)),
) -> JobOut:
    try:
        job = retry_job(
            session,
            actor=principal.actor,
            created_by=principal.created_by,
            job_id=job_id,
        )
    except ServiceError as exc:
        abort(exc)
    body = _out(job)
    session.commit()
    return body


def _out(job: Job) -> JobOut:
    payload = job.payload
    copied: dict[str, Any] = dict(payload) if isinstance(payload, dict) else {}
    return JobOut(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        payload=copied,
        attempts=job.attempts,
        run_at=job.run_at,
        locked_by=job.locked_by,
        last_error=job.last_error,
        created_at=job.created_at,
    )
