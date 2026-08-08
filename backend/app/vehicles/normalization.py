"""Vehicle registration-number normalization.

Formatting differs across documents (12345678 / 123-45-678 / 12-345-67). We
normalize to digits-only so matching is reliable and deterministic.
"""

from __future__ import annotations

import re

_NON_DIGIT = re.compile(r"\D+")


def normalize_registration(raw: str | None) -> str:
    """Return digits-only canonical form; empty string for falsy input."""
    if not raw:
        return ""
    return _NON_DIGIT.sub("", raw)


def registration_matches(a: str | None, b: str | None) -> bool:
    na, nb = normalize_registration(a), normalize_registration(b)
    return bool(na) and na == nb
