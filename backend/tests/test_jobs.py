"""Two workers must not claim the same job. Failures keep last_error and back off."""

import threading
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete

from app.core.config import get_settings
from app.models.enums import JobStatus, RoleCode
from app.models.ops import AuditLog, Job
from app.services.jobs import (
    _CLAIM_SQL,
    HANDLERS,
    backoff_seconds,
    claim,
    enqueue,
    process_next,
)
from tests.foundation import Foundation


def test_claim_sql_locks_one_row() -> None:
    compact = " ".join(_CLAIM_SQL.split())
    assert "SELECT TOP 1 id" in compact
    assert "WITH (UPDLOCK, READPAST, ROWLOCK)" in compact
    assert "ORDER BY run_at, id" in compact


def test_backoff_doubles_until_the_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JOB_BACKOFF_BASE_SECONDS", "10")
    monkeypatch.setenv("JOB_BACKOFF_MAX_SECONDS", "25")
    get_settings.cache_clear()
    try:
        assert backoff_seconds(1) == 10
        assert backoff_seconds(2) == 20
        assert backoff_seconds(3) == 25
    finally:
        get_settings.cache_clear()


def test_two_workers_never_claim_the_same_job(foundation: Foundation) -> None:
    _clear_jobs(foundation)
    job_id = _insert_job(foundation, "one")
    found = _claim_together(foundation, 2)
    assert sorted(found, key=lambda value: (value is None, value)) == [job_id, None]


def test_two_workers_claim_different_jobs(foundation: Foundation) -> None:
    _clear_jobs(foundation)
    first = _insert_job(foundation, "alpha")
    second = _insert_job(foundation, "beta")
    found = _claim_together(foundation, 2)
    assert set(found) == {first, second}


def test_a_future_job_is_not_claimed(foundation: Foundation) -> None:
    _clear_jobs(foundation)
    with foundation.factory() as session:
        job = enqueue(
            session,
            job_type="later",
            payload={},
            run_at=datetime.now(UTC) + timedelta(hours=1),
        )
        session.commit()
        assert claim(session, "worker-a") is None
        stored = session.get(Job, job.id)
        assert stored is not None
        assert stored.status == JobStatus.pending


def test_unknown_job_fails_once(foundation: Foundation) -> None:
    _clear_jobs(foundation)
    job_id = _insert_job(foundation, "not-a-real-job")
    with foundation.factory() as session:
        assert process_next(session, "worker-a") is True
        stored = session.get(Job, job_id)
        assert stored is not None
        assert stored.status == JobStatus.failed
        assert stored.attempts == 1
        assert stored.last_error == "no handler registered for not-a-real-job"
        assert process_next(session, "worker-b") is False


def test_handler_failure_retries_then_stops(
    foundation: Foundation,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JOB_MAX_ATTEMPTS", "2")
    monkeypatch.setenv("JOB_BACKOFF_BASE_SECONDS", "30")
    monkeypatch.setenv("JOB_BACKOFF_MAX_SECONDS", "120")
    get_settings.cache_clear()
    _clear_jobs(foundation)

    def explode(_payload: dict[str, object]) -> None:
        raise RuntimeError("nope")

    HANDLERS["explode"] = explode
    try:
        job_id = _insert_job(foundation, "explode")
        with foundation.factory() as session:
            assert process_next(session, "worker-a") is True
            stored = session.get(Job, job_id)
            assert stored is not None
            assert stored.status == JobStatus.pending
            assert stored.last_error == "nope"
            assert stored.attempts == 1
            assert stored.locked_by is None
            assert stored.run_at is not None
            stored.run_at = datetime.now(UTC) - timedelta(seconds=1)
            session.commit()
            assert process_next(session, "worker-b") is True
            session.refresh(stored)
            assert stored.status == JobStatus.failed
            assert stored.attempts == 2
            assert stored.last_error == "nope"
    finally:
        HANDLERS.pop("explode", None)
        get_settings.cache_clear()


def test_registered_handler_completes(foundation: Foundation) -> None:
    _clear_jobs(foundation)
    seen: dict[str, object] = {}

    def handler(payload: dict[str, object]) -> None:
        seen["payload"] = payload

    HANDLERS["ping"] = handler
    try:
        job_id = _insert_job(foundation, "ping", {"ok": True})
        with foundation.factory() as session:
            assert process_next(session, "worker-a") is True
            stored = session.get(Job, job_id)
            assert stored is not None
            assert stored.status == JobStatus.succeeded
            assert stored.attempts == 1
        assert seen["payload"] == {"ok": True}
    finally:
        HANDLERS.pop("ping", None)


def test_admin_lists_and_retries_a_failed_job(foundation: Foundation) -> None:
    _clear_jobs(foundation)
    with foundation.factory() as session:
        job = Job(
            job_type="odoo_writeback",
            payload={"task": 1},
            status=JobStatus.failed,
            attempts=5,
            last_error="boom",
        )
        session.add(job)
        session.commit()
        job_id = job.id

    client = foundation.login(RoleCode.admin)
    listed = client.get("/api/jobs", params={"status": "failed"})
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == job_id
    assert listed.json()[0]["last_error"] == "boom"

    retried = client.post(f"/api/jobs/{job_id}/retry")
    assert retried.status_code == 200
    assert retried.json()["status"] == "pending"
    assert retried.json()["attempts"] == 0
    assert retried.json()["locked_by"] is None

    again = client.post(f"/api/jobs/{job_id}/retry")
    assert again.status_code == 409
    missing = client.post("/api/jobs/999999/retry")
    assert missing.status_code == 404

    audit = client.get("/api/audit-log", params={"entity": "job", "entity_id": str(job_id)})
    assert audit.status_code == 200
    assert audit.json()[0]["action"] == "job.retry"
    assert audit.json()[0]["actor"] == foundation.emails[RoleCode.admin]

    foundation.login(RoleCode.viewer)
    assert foundation.client.get("/api/jobs").status_code == 403
    foundation.login(RoleCode.tester)
    assert foundation.client.post(f"/api/jobs/{job_id}/retry").status_code == 403

    with foundation.factory() as session:
        row = session.get(AuditLog, audit.json()[0]["id"])
        assert row is not None
        assert row.before == {"status": "failed", "attempts": 5, "locked_by": None}
        assert row.after == {"status": "pending", "attempts": 0, "locked_by": None}


def _clear_jobs(foundation: Foundation) -> None:
    with foundation.factory() as session:
        session.execute(delete(Job))
        session.commit()


def _insert_job(
    foundation: Foundation,
    job_type: str,
    payload: dict[str, object] | None = None,
) -> int:
    with foundation.factory() as session:
        job = enqueue(session, job_type=job_type, payload=payload or {})
        session.commit()
        return job.id


def _claim_together(foundation: Foundation, workers: int) -> list[int | None]:
    barrier = threading.Barrier(workers)
    found: list[int | None] = []
    errors: list[BaseException] = []
    lock = threading.Lock()

    def run(name: str) -> None:
        session = foundation.factory()
        try:
            barrier.wait(timeout=5)
            job = claim(session, name)
            with lock:
                found.append(None if job is None else job.id)
        except Exception as exc:
            with lock:
                errors.append(exc)
        finally:
            session.close()

    threads = [threading.Thread(target=run, args=(f"worker-{index}",)) for index in range(workers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
        assert not thread.is_alive()
    assert errors == []
    return found
