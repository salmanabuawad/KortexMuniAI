"""Sensitive-data detection + sanitization for manual global-AI escalation (spec §7).

Deterministic regex-based detection. Order matters: more specific patterns run
first so a phone number isn't mistaken for an ID, etc. Values are replaced with
stable placeholders ([EMAIL], [PHONE], [ID], [VEHICLE], [ACCOUNT], [IP], [URL]).

IMPORTANT: sanitization is NEVER claimed to be perfect. Personal *names* and
free-text addresses are not reliably detectable by regex and are NOT removed —
the authorized user must review and edit the generated prompt before copying it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Ordered (label, placeholder, pattern). First match wins per span.
_PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    ("email", "[EMAIL]", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("url", "[URL]", re.compile(r"\bhttps?://[^\s]+", re.IGNORECASE)),
    ("iban", "[ACCOUNT]", re.compile(r"\bIL\d{2}[\d ]{15,23}\b", re.IGNORECASE)),
    ("credit_card", "[ACCOUNT]", re.compile(r"\b(?:\d[ -]?){13,19}\b")),
    # Israeli phone: +972 or 0, area/prefix, 7 digits, optional separators.
    ("phone", "[PHONE]", re.compile(r"\b(?:\+972[-\s]?|0)(?:\d[-\s]?){8,9}\d\b")),
    # Israeli vehicle plate: 7-8 digits commonly grouped NN-NNN-NN / NNN-NN-NNN.
    ("vehicle", "[VEHICLE]", re.compile(r"\b\d{2,3}-\d{2,3}-\d{2,3}\b")),
    # Israeli ID / Teudat Zehut: exactly 9 digits (after the above ran).
    ("id", "[ID]", re.compile(r"\b\d{9}\b")),
    ("ip", "[IP]", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
]


@dataclass
class SanitizationResult:
    text: str
    detected: dict[str, int] = field(default_factory=dict)  # type -> count

    @property
    def types(self) -> list[str]:
        return sorted(self.detected)

    @property
    def sensitivity(self) -> str:
        n = sum(self.detected.values())
        if n == 0:
            return "low"
        if self.detected.get("id") or self.detected.get("credit_card") or self.detected.get("iban"):
            return "high"
        return "medium"


def sanitize(text: str) -> SanitizationResult:
    detected: dict[str, int] = {}
    out = text
    for label, placeholder, pattern in _PATTERNS:
        def repl(_: re.Match[str], _label=label, _ph=placeholder) -> str:
            detected[_label] = detected.get(_label, 0) + 1
            return _ph
        out = pattern.sub(repl, out)
    return SanitizationResult(text=out, detected=detected)
