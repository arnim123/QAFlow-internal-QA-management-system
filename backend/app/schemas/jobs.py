"""Job queue payloads."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.enums import JobStatus


class JobOut(BaseModel):
    id: int
    job_type: str
    status: JobStatus
    payload: dict[str, Any]
    attempts: int
    run_at: datetime | None
    locked_by: str | None
    last_error: str | None
    created_at: datetime
