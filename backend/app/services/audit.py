"""Durable audit log. State changes still enter through workflow.record_state_change."""

from collections.abc import Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ops import AuditLog


def record(
    session: Session,
    *,
    actor: str,
    action: str,
    entity: str,
    entity_id: str,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
    created_by: int | None = None,
) -> AuditLog:
    """Insert one audit row. The caller commits."""

    row = AuditLog(
        actor=actor,
        action=action,
        entity=entity,
        entity_id=entity_id,
        before=None if before is None else dict(before),
        after=None if after is None else dict(after),
        created_by=created_by,
    )
    session.add(row)
    session.flush()
    return row


def audited(action: str, entity: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Wrap a service that returns `(result, entity_id, before, after)`.

    The wrapped function takes `session` and `actor`, and may take `created_by`.
    Callers receive `result`. The audit row is written through workflow.py.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result, entity_id, before, after = fn(*args, **kwargs)
            session = kwargs.get("session")
            if session is None and args:
                session = args[0]
            from app.services.workflow import record_state_change

            record_state_change(
                session=session,
                entity=entity,
                entity_id=str(entity_id),
                action=action,
                actor=kwargs["actor"],
                before=before,
                after=after,
                created_by=kwargs.get("created_by"),
            )
            return result

        wrapper.__name__ = fn.__name__
        wrapper.__doc__ = fn.__doc__
        return wrapper

    return decorator


def list_audit(
    session: Session,
    *,
    entity: str | None = None,
    entity_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[AuditLog]:
    bounded = min(max(limit, 1), 200)
    stmt = select(AuditLog).order_by(AuditLog.id.desc())
    if entity is not None:
        stmt = stmt.where(AuditLog.entity == entity)
    if entity_id is not None:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    return list(session.scalars(stmt.offset(max(offset, 0)).limit(bounded)))
