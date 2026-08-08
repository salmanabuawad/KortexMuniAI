"""Structured-first QA regression tests (spec Part 16).

Deterministic: intent detection is pure; field values come from the extractor's
stored JSON on the fixture PDF. No LLM, no DB. The follow-up test proves that a
terse second question ("תחילה") resolves independently of the previous one.
"""

from __future__ import annotations

import os.path

import pytest

from app.rag.structured_qa import (
    detect_structured_intent,
    field_from_extraction_json,
    format_field_answer,
)

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "mandatory_insurance_sample.pdf")


@pytest.fixture(scope="module")
def extraction_json():
    if not os.path.exists(FIXTURE):
        pytest.skip("real sample PDF not present (PII, not committed)")
    pytest.importorskip("pymupdf")
    from app.vehicles.extraction import extract_document
    return extract_document(FIXTURE, "pdf").as_dict()


def _answer(extraction_json, question) -> str | None:
    """Simulate the deterministic path: intent -> stored field -> formatted value."""
    intent = detect_structured_intent(question)
    if not intent.field:
        return None
    fv = field_from_extraction_json(extraction_json, intent.field)
    return fv.value if fv else None


# --- intent detection (pure, no PDF) -----------------------------------------

@pytest.mark.parametrize("q,field", [
    ("מה מספר הרכב", "vehicle_number"),
    ("מספר רישוי", "vehicle_number"),
    ("רכב", "vehicle_number"),          # terse
    ("תחילה", "insurance_start"),        # terse follow-up
    ("תחילת הביטוח", "insurance_start"),
    ("תום", "insurance_end"),            # terse follow-up
    ("תום הביטוח", "insurance_end"),
    ("מספר פוליסה", "policy_number"),
    ("פוליסה", "policy_number"),
    ("מי בעל הפוליסה", "policy_holder"),
    ("מחיר", "premium"),
    ("رقم السيارة", "vehicle_number"),
    ("بداية التأمين", "insurance_start"),
    ("vehicle number", "vehicle_number"),
    ("insurance expiry", "insurance_end"),
])
def test_intent(q, field):
    assert detect_structured_intent(q).field == field


def test_open_question_has_no_structured_intent():
    assert detect_structured_intent("מה התנאים לביטול הפוליסה?").field is None
    assert detect_structured_intent("what are the cancellation conditions?").field is None


# --- field values from the real fixture --------------------------------------

@pytest.mark.parametrize("q,expected", [
    ("מה מספר הרכב", "7046676"),
    ("מספר רישוי", "7046676"),
    ("תחילה", "2026-08-02"),
    ("תחילת הביטוח", "2026-08-02"),
    ("תום", "2026-08-15"),
    ("תום הביטוח", "2026-08-15"),
    ("מספר פוליסה", "201-502525667826-00"),
    ("מי בעל הפוליסה", "אבו עואד נדא"),
])
def test_field_values(extraction_json, q, expected):
    assert _answer(extraction_json, q) == expected


def test_premium_is_234(extraction_json):
    assert "234" in (_answer(extraction_json, "מחיר") or "")


def test_vehicle_number_negatives(extraction_json):
    v = _answer(extraction_json, "מה מספר הרכב")
    assert v not in {"37005618", "1197", "2012"}


def test_followup_flow_independent(extraction_json):
    # Q1 end date, Q2 terse start — the second MUST NOT return the end date.
    a1 = _answer(extraction_json, "תום הביטוח")
    a2 = _answer(extraction_json, "תחילה")
    assert a1 == "2026-08-15"
    assert a2 == "2026-08-02"
    assert a1 != a2


def test_formatted_answer_dates_and_no_noise():
    ans = format_field_answer("insurance_start", "2026-08-02", "he")
    assert "02/08/2026" in ans
    ans_v = format_field_answer("vehicle_number", "7046676", "he")
    assert "7046676" in ans_v and "1197" not in ans_v and "2012" not in ans_v
