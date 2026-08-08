"""Orchestrates an external-AI (OpenAI) escalation: build MINIMAL redacted context
from local retrieval, apply policy, call OpenAI, and audit — reused by automatic
mode and the manual /chat/escalate endpoint.

Only the minimal relevant, redacted context leaves the server (spec §10/§11/§31);
whole PDFs are never sent.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.ai.policy import can_send_to_external_ai
from app.ai.providers.openai_provider import openai_service
from app.ai.redaction import redact
from app.core.config import settings
from app.core.logging import get_logger
from app.models.audit import ExternalAIAudit
from app.models.iam import User
from app.rag.postprocess import clean_answer
from app.rag.retrieval import retrieve
from app.rag.service import build_context_block

logger = get_logger("muniai.ai.escalation")


@dataclass
class EscalationResult:
    ok: bool
    answer: str = ""
    model: str | None = None
    provider: str = "openai"
    reason: str | None = None
    sources: list[dict] = field(default_factory=list)
    usage: dict = field(default_factory=dict)


async def _build_minimal_context(db: Session, user: User, question: str, document_id):
    """Local retrieval -> dedupe/rerank/clean -> redact -> truncate. Returns
    (context_text, sources, redaction_applied, char_count)."""
    retrieved = await retrieve(db, user, question, document_id=document_id)
    context_block, citations = build_context_block(retrieved, question)
    red_text, detected = redact(context_block)
    red_text = red_text[: settings.openai_max_context_chars]
    sources = [{"document": c.document_title, "page": c.page, "document_id": c.document_id}
               for c in citations]
    return red_text, sources, bool(detected), len(red_text)


async def run_escalation(db: Session, user: User, conversation, question: str,
                         document_id=None, cfg: dict | None = None) -> EscalationResult:
    model = (cfg or {}).get("openai_model") or settings.openai_model
    context, sources, redacted, nchars = await _build_minimal_context(
        db, user, question, document_id
    )

    audit = ExternalAIAudit(
        user_id=user.id,
        conversation_id=getattr(conversation, "id", None),
        document_id=str(document_id) if document_id else None,
        model=model, request_type="escalation",
        redaction_applied=redacted, context_character_count=nchars,
        department=(user.department.name if getattr(user, "department", None) else None),
    )

    decision = can_send_to_external_ai(user, f"{question}\n{context}", cfg)
    if not decision.allowed:
        audit.success = False
        audit.error_code = decision.reason
        db.add(audit)
        db.commit()
        return EscalationResult(False, reason=decision.reason, sources=sources)

    res = await openai_service.answer(question, context, model=model)
    audit.success = res.ok
    audit.error_code = res.error_code
    audit.latency_ms = res.latency_ms
    audit.input_tokens = res.input_tokens
    audit.output_tokens = res.output_tokens
    db.add(audit)
    db.commit()

    if not res.ok:
        return EscalationResult(False, reason=res.error_code or "error", sources=sources)
    return EscalationResult(
        True, answer=clean_answer(res.answer), model=res.model,
        sources=sources, usage=res.usage,
    )
