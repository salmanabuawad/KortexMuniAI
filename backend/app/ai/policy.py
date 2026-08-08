"""Central policy: may this request go to the external AI? (spec §12/§13).

One place decides — routes never scatter these checks.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.ai.redaction import blocked_category
from app.core.config import settings
from app.models.iam import User


@dataclass
class ExternalAIDecision:
    allowed: bool
    reason: str
    blocked_category: str | None = None


def can_send_to_external_ai(user: User, text: str, cfg: dict | None = None) -> ExternalAIDecision:
    # cfg is the effective runtime config (DB over env); fall back to env.
    configured = cfg["openai_configured"] if cfg else settings.openai_configured
    mode = cfg["openai_escalation_mode"] if cfg else settings.openai_escalation_mode
    if not configured:
        return ExternalAIDecision(False, "openai_not_configured")
    if mode == "disabled":
        return ExternalAIDecision(False, "escalation_disabled")

    keys = user.permission_keys
    if not ("*" in keys or "GLOBAL_AI_ESCALATION:*" in keys or "GLOBAL_AI_ESCALATION" in keys):
        return ExternalAIDecision(False, "user_not_permitted")

    cat = blocked_category(text)
    if cat:
        return ExternalAIDecision(False, "blocked_category", blocked_category=cat)

    return ExternalAIDecision(True, "ok")
