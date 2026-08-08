"""Manual global-AI escalation (spec §7).

Builds a sanitized, copy-pasteable prompt for an external AI. MuniAI never
transmits anything automatically; the user reviews/edits and copies it. Imported
answers are stored clearly labelled as externally generated and are NOT treated
as organizational truth without approval.

The audit record does NOT store the sensitive prompt contents — only metadata
(reason, sensitivity, detected types, flags).
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.escalation.sanitizer import sanitize
from app.models.audit import ExternalAIEscalation

PROMPT_TEMPLATE = """GLOBAL AI ASSISTANCE REQUEST

Problem:
{problem}

Relevant non-sensitive context:
{context}

Question:
{question}

Requirements:
- Use only the information provided above.
- Do not ask for identifying personal data.
- Provide clear reasoning and, where relevant, cite which part of the context you used.
"""


def build_prompt(question: str, context: str = "", problem: str = "") -> tuple[str, dict]:
    """Return (sanitized_prompt, meta). meta has detected types + sensitivity."""
    s_question = sanitize(question)
    s_context = sanitize(context or "(none provided)")
    s_problem = sanitize(problem or "A municipal question the local model was not confident answering.")

    detected: dict[str, int] = {}
    for part in (s_question, s_context, s_problem):
        for k, v in part.detected.items():
            detected[k] = detected.get(k, 0) + v

    sensitivity = "high" if any(
        detected.get(k) for k in ("id", "credit_card", "iban")
    ) else ("medium" if detected else "low")

    prompt = PROMPT_TEMPLATE.format(
        problem=s_problem.text, context=s_context.text, question=s_question.text
    )
    return prompt, {"detected_types": sorted(detected), "sensitivity": sensitivity}


def record_escalation(
    db: Session,
    *,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID | None,
    meta: dict,
    reason: str = "Local model low confidence",
) -> ExternalAIEscalation:
    ev = ExternalAIEscalation(
        user_id=user_id,
        conversation_id=conversation_id,
        reason=reason,
        data_sensitivity=meta.get("sensitivity"),
        sensitive_types_detected=meta.get("detected_types", []),
        prompt_generated=True,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev
