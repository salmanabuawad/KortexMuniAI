"""Audit engine — record important activity (spec §34).

Never logs passwords, tokens, or full confidential prompt/document contents.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.audit import AuditEvent

logger = get_logger("muniai.audit")


def record(
    db: Session,
    *,
    action: str,
    user_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    result: str = "success",
    ip_address: str | None = None,
    detail: str | None = None,
    session_meta: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        result=result,
        ip_address=ip_address,
        detail=detail,
        session_meta=session_meta or {},
    )
    db.add(event)
    db.commit()
    logger.info("audit action=%s user=%s result=%s", action, user_id, result)
    return event
