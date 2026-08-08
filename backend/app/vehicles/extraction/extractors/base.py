"""Shared field resolution used by the per-document-type extractors."""

from __future__ import annotations

from datetime import date

from dateutil import parser as dateparser

from app.vehicles.extraction.anchors import best_field_for_phrase
from app.vehicles.extraction.candidate_scoring import (
    confidence_from_score,
    score_vehicle_candidates,
)
from app.vehicles.extraction.layout import LabelHit, group_rows, resolve_value
from app.vehicles.extraction.normalizer import digits_only
from app.vehicles.extraction.schemas import ExtractionResult, Field, Word

INSURERS = ["הראל", "כלל", "מגדל", "הפניקס", "מנורה", "איילון", "שלמה",
            "ביטוח ישיר", "הכשרה", "AIG"]


def _row_of(word: Word, rows: list[list[Word]]) -> list[Word]:
    for row in rows:
        if word in row:
            return row
    return [word]


def resolve_numeric_field(label: LabelHit, words: list[Word]) -> Field | None:
    w, score, rel = resolve_value(label, words, numeric_only=True)
    if not w:
        return None
    return Field(
        value=digits_only(w.text) or w.text.strip(),
        confidence=confidence_from_score(score) * max(w.conf, 0.5),
        source="pdf_text_layout" if w.source == "pdf_text" else w.source,
        page=w.page, label_detected=label.text,
        reason=f"{rel} label {label.text!r}",
    )


def resolve_raw_field(label: LabelHit, words: list[Word]) -> Field | None:
    """Resolve a value token but keep its original formatting (policy numbers,
    premiums, VINs — never reduce these to bare digits)."""
    w, score, rel = resolve_value(label, words, numeric_only=True)
    if not w:
        return None
    return Field(
        value=w.text.strip(" :־-"),
        confidence=confidence_from_score(score) * max(w.conf, 0.5),
        source="pdf_text_layout" if w.source == "pdf_text" else w.source,
        page=w.page, label_detected=label.text, reason=f"{rel} label {label.text!r}",
    )


def resolve_text_field(label: LabelHit, words: list[Word]) -> Field | None:
    """Resolve a multi-token text value (e.g. a name) beside/below a label."""
    rows = group_rows(words)
    label_row = None
    for row in rows:
        if any(abs(w.cy - label.cy) <= label.h * 0.6 for w in row):
            label_row = row
            break

    value_tokens: list[Word] = []

    # Prefer the row directly below, column-aligned (label-over-value forms — the
    # common Israeli certificate layout). This avoids grabbing a neighbouring
    # label that shares the same label row.
    below_rows = [r for r in rows if r and min(w.cy for w in r) > label.y1 - label.h * 0.3]
    below_rows.sort(key=lambda r: min(w.cy for w in r))
    for r in below_rows:
        col = [w for w in r if w.text.strip()
               and w.x1 >= label.x0 - label.h and w.x0 <= label.x1 + label.h
               and any(ch.isalpha() for ch in w.text)
               and best_field_for_phrase(w.text)[0] is None]  # skip other labels
        if col:
            value_tokens = col
            break

    # Otherwise the value is beside the label (inline "label: value" — RTL puts
    # the value to the left). Exclude tokens that are themselves labels.
    if not value_tokens and label_row:
        value_tokens = [w for w in label_row
                        if w.x1 <= label.x0 + 1 and w.text.strip()
                        and not _is_label_token(w, label)
                        and best_field_for_phrase(w.text)[0] is None]
        if not value_tokens:
            value_tokens = [w for w in label_row
                            if w.x0 >= label.x1 - 1 and w.text.strip()
                            and best_field_for_phrase(w.text)[0] is None]

    if not value_tokens:
        w, score, _ = resolve_value(label, words)
        if not w:
            return None
        value_tokens = [w]

    # Hebrew values read right-to-left, so order tokens by descending x.
    value_tokens.sort(key=lambda w: -w.x0)
    text = " ".join(w.text for w in value_tokens).strip(" :־-")
    # Reject punctuation-only / too-short fragments (common in messy RTL PDFs).
    if len(text) < 2 or not any(ch.isalpha() for ch in text):
        return None
    tok_conf = min(w.conf for w in value_tokens) if value_tokens else 0.6
    # Text fields on fragmented RTL layouts are inherently uncertain — keep the
    # confidence modest so the review UI always flags them for confirmation.
    return Field(value=text, confidence=0.6 * tok_conf,
                 source="pdf_text_layout" if value_tokens[0].source == "pdf_text" else value_tokens[0].source,
                 page=label.page, label_detected=label.text, reason="text near label")


def _is_label_token(w: Word, label: LabelHit) -> bool:
    return label.x0 - 1 <= w.cx <= label.x1 + 1 and label.y0 - 1 <= w.cy <= label.y1 + 1


def resolve_date_field(label: LabelHit, words: list[Word]) -> Field | None:
    w, score, rel = resolve_value(label, words)
    if not w:
        return None
    try:
        d = dateparser.parse(w.text, dayfirst=True).date()
    except (ValueError, OverflowError, TypeError):
        return None
    return Field(value=d.isoformat(), confidence=confidence_from_score(score) * max(w.conf, 0.5),
                 source="layout", page=w.page, label_detected=label.text,
                 reason=f"{rel} label {label.text!r}")


def add_vehicle_number(result: ExtractionResult, words: list[Word], labels: list[LabelHit]) -> None:
    candidates = score_vehicle_candidates(words, labels)
    result.vehicle_candidates = candidates
    chosen = next((c for c in candidates if c.selected), None)
    if chosen:
        conf = confidence_from_score(chosen.score)
        # A 7-8 digit value sitting under a מס' רישוי label is a strong signal —
        # give it auto-populate confidence so the UI fills it without asking.
        if chosen.score >= 150:
            conf = max(conf, 0.9)
        result.fields["vehicle_number"] = Field(
            value=chosen.value,
            confidence=conf,
            source="pdf_text_layout",
            page=chosen.page,
            label_detected=chosen.label,
            reason=chosen.reason,
        )
    else:
        result.warnings.append("vehicle_number: no confident candidate")


def add_simple_fields(result: ExtractionResult, words: list[Word], labels: list[LabelHit],
                      *, numeric=(), raw=(), text=(), dates=()) -> None:
    by_field: dict[str, list[LabelHit]] = {}
    for h in labels:
        by_field.setdefault(h.field, []).append(h)

    for fld in numeric:
        for lab in by_field.get(fld, []):
            f = resolve_numeric_field(lab, words)
            if f and f.value:
                result.fields.setdefault(fld, f)
                break
    for fld in raw:
        for lab in by_field.get(fld, []):
            f = resolve_raw_field(lab, words)
            if f and f.value:
                result.fields.setdefault(fld, f)
                break
    for fld in text:
        for lab in by_field.get(fld, []):
            f = resolve_text_field(lab, words)
            if f and f.value:
                result.fields.setdefault(fld, f)
                break
    for fld in dates:
        for lab in by_field.get(fld, []):
            f = resolve_date_field(lab, words)
            if f and f.value:
                result.fields.setdefault(fld, f)
                break


def detect_insurer(text: str) -> Field | None:
    for name in INSURERS:
        if name in text:
            return Field(value=name, confidence=0.7, source="regex", reason="insurer name match")
    return None


import re  # noqa: E402

# Israeli policy numbers commonly look like 201-502525667826-00 (grouped, dashed).
_POLICY_RE = re.compile(r"\b\d{3}-\d{6,}-\d{2}\b")


def detect_policy_number(text: str) -> Field | None:
    m = _POLICY_RE.search(text or "")
    if m:
        return Field(value=m.group(0), confidence=0.85, source="regex",
                     reason="matched policy-number pattern")
    return None
