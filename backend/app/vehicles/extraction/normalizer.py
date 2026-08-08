"""Normalization helpers for Hebrew labels and numeric values."""

from __future__ import annotations

import re

# Gershayim/geresh and quote variants used interchangeably in Hebrew labels.
_QUOTES = "\"'`״׳‘’“”"
_QUOTE_RE = re.compile(f"[{re.escape(_QUOTES)}]")
_WS_RE = re.compile(r"\s+")
_NON_DIGIT = re.compile(r"\D+")

# Conservative OCR confusions to try only for numeric fields when a token is
# *almost* all digits (e.g. a stray O/o/l/I among digits).
_OCR_DIGIT_MAP = str.maketrans({"O": "0", "o": "0", "Q": "0", "D": "0",
                                "I": "1", "l": "1", "|": "1",
                                "S": "5", "B": "8", "Z": "2", "g": "9"})


def normalize_label(s: str) -> str:
    """Canonicalize a Hebrew label for matching: drop quotes/gershayim, collapse
    whitespace, strip trailing punctuation."""
    s = _QUOTE_RE.sub("", s)
    s = s.replace("‏", "").replace("‎", "")  # RTL/LTR marks
    s = _WS_RE.sub(" ", s).strip()
    return s.strip(" :.-")


def digits_only(s: str) -> str:
    return _NON_DIGIT.sub("", s or "")


def ocr_fix_digits(s: str) -> str:
    """Fix obvious OCR confusions in a token that should be numeric."""
    return s.translate(_OCR_DIGIT_MAP)


def looks_like_year(s: str) -> bool:
    d = digits_only(s)
    return len(d) == 4 and 1950 <= int(d) <= 2099


def looks_like_phone(s: str) -> bool:
    d = digits_only(s)
    return len(d) in (9, 10) and d.startswith("0")


def looks_like_money(s: str) -> bool:
    return bool(re.search(r"\d[\d,]*\.\d{2}\b", s)) or "₪" in s


def looks_like_date(s: str) -> bool:
    return bool(re.search(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b", s))
