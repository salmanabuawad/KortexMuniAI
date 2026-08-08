"""Global-AI escalation endpoints (manual, user-controlled — spec §7).

/prepare returns a sanitized prompt for the user to review, edit and copy. Nothing
is transmitted to any external AI. /import stores a user-pasted external answer,
clearly labelled EXTERNAL_IMPORTED (never auto-promoted to knowledge).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.v1.schemas import (
    EscalationImportRequest,
    EscalationPrepareRequest,
    EscalationPrepareResponse,
    MessageOut,
)
from app.audit import service as audit
from app.auth.deps import client_ip, require_permission
from app.core.errors import MuniAIError
from app.db.session import get_db
from app.escalation.service import build_prompt, record_escalation
from app.models.chat import Conversation, Message
from app.models.enums import AnswerOrigin, MessageRole
from app.models.iam import User

router = APIRouter(prefix="/escalation", tags=["escalation"])


@router.post("/prepare", response_model=EscalationPrepareResponse)
def prepare(
    payload: EscalationPrepareRequest,
    request: Request,
    user: User = Depends(require_permission("GLOBAL_AI_ESCALATION")),
    db: Session = Depends(get_db),
) -> EscalationPrepareResponse:
    prompt, meta = build_prompt(payload.question, payload.context or "")
    ev = record_escalation(
        db, user_id=user.id, conversation_id=payload.conversation_id, meta=meta
    )
    audit.record(
        db, action="global_ai_prompt_generated", user_id=user.id,
        resource_type="escalation", resource_id=ev.id, ip_address=client_ip(request),
        detail=f"sensitivity={meta['sensitivity']} types={','.join(meta['detected_types'])}",
    )
    return EscalationPrepareResponse(
        escalation_id=ev.id, prompt=prompt,
        detected_types=meta["detected_types"], sensitivity=meta["sensitivity"],
    )


@router.post("/import", response_model=MessageOut)
def import_answer(
    payload: EscalationImportRequest,
    request: Request,
    user: User = Depends(require_permission("GLOBAL_AI_ESCALATION")),
    db: Session = Depends(get_db),
) -> Message:
    convo = db.get(Conversation, payload.conversation_id)
    if not convo or convo.user_id != user.id:
        raise MuniAIError("Conversation not found.", status_code=404, code="not_found")

    msg = Message(
        conversation_id=convo.id,
        role=MessageRole.ASSISTANT,
        content=payload.answer,
        origin=AnswerOrigin.EXTERNAL_IMPORTED,
        model="external (user-imported)",
        provider="external",
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    audit.record(
        db, action="global_ai_answer_imported", user_id=user.id,
        resource_type="conversation", resource_id=convo.id, ip_address=client_ip(request),
    )
    return msg
