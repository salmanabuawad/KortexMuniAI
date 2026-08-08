"""Redaction + blocked-category detection for data leaving the server (spec §11/§13).

Reuses the tested PII sanitizer (Israeli ID, phone, email, IBAN, card, plate,
IP, URL). Names/addresses are NOT reliably detectable by regex — we never claim
perfect redaction; the manual-escalation consent step covers that residual risk.
"""

from __future__ import annotations

import re

from app.core.config import settings
from app.escalation.sanitizer import sanitize

# Terms that must NEVER be sent externally (credentials/secrets), matched loosely.
_BLOCKED_PATTERNS = {
    "password": re.compile(r"\b(password|סיסמ[הא]|كلمة\s*المرور)\b", re.IGNORECASE),
    "token": re.compile(r"\b(token|bearer\s+[\w.\-]+|טוקן)\b", re.IGNORECASE),
    "api_key": re.compile(r"\b(api[_-]?key|sk-[A-Za-z0-9]{10,})\b", re.IGNORECASE),
    "credential": re.compile(r"\b(credential|credentials|אישורי\s*גישה)\b", re.IGNORECASE),
    "secret": re.compile(r"\b(secret|private\s*key|-----BEGIN)\b", re.IGNORECASE),
}


def blocked_category(text: str) -> str | None:
    """Return the first blocked category found, or None."""
    for cat in settings.blocked_categories:
        pat = _BLOCKED_PATTERNS.get(cat)
        if pat and pat.search(text or ""):
            return cat
    return None


# Israeli IDs are 9 digits but frequently written as 8 (leading zero dropped).
# The shared sanitizer only catches 9; for external redaction we also mask 8.
_ID8 = re.compile(r"(?<!\d)\d{8}(?!\d)")


def redact(text: str) -> tuple[str, list[str]]:
    """Return (redacted_text, detected_types). No-op when redaction is disabled."""
    if not settings.openai_redaction_enabled or not text:
        return text, []
    result = sanitize(text)
    out = result.text
    types = list(result.types)
    if _ID8.search(out):
        out = _ID8.sub("[ID]", out)
        if "id" not in types:
            types.append("id")
    return out, sorted(types)
