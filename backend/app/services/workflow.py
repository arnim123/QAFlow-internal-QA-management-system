"""The only seam for QAFlow state changes.

Call `record_state_change` for every transition. Pass a session when the change
is being committed so the audit log row is written in the same transaction.
Do not change workflow state anywhere else.
"""

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.services.audit import record

logger = logging.getLogger(__name__)


def record_state_change(
    *,
    entity: str,
    entity_id: str,
    action: str,
    actor: str,
    reason: str | None = None,
    details: dict[str, Any] | None = None,
    session: Session | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    created_by: int | None = None,
) -> None:
    """Record who changed what, and when."""

    logger.info(
        "state change",
        extra={
            "audit": True,
            "entity": entity,
            "entity_id": entity_id,
            "action": action,
            "actor": actor,
            "reason": reason,
            "details": details or {},
        },
    )
    if session is None:
        return
    stored_after: dict[str, Any] | None
    if after is None and reason is None:
        stored_after = None
    else:
        stored_after = dict(after or {})
        if reason:
            stored_after["reason"] = reason
    record(
        session,
        actor=actor,
        action=action,
        entity=entity,
        entity_id=entity_id,
        before=None if before is None else dict(before),
        after=stored_after,
        created_by=created_by,
    )
