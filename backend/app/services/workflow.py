"""The only seam for QAFlow state changes.

Call `record_state_change` for every transition. `audit_log` is the durable
record, but this function still writes a structured log line. Inserting the
row belongs with the workflow service, which is not wired yet.
Do not change workflow state anywhere else.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def record_state_change(
    *,
    entity: str,
    entity_id: str,
    action: str,
    actor: str,
    reason: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Record who changed what, and when. Does not insert into `audit_log` yet."""

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
