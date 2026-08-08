"""Regression tests for field-aware vehicle-document extraction.

The headline requirement: the mandatory-insurance certificate must yield
vehicle_number == "7046676" and must NEVER return the ID number 37005618.
"""

from __future__ import annotations

import pytest

from app.vehicles.extraction import extract_from_words
from app.vehicles.extraction.candidate_scoring import score_vehicle_candidates
from app.vehicles.extraction.classifier import classify_document
from app.vehicles.extraction.layout import find_label_hits
from tests.fixtures.mandatory_insurance_words import build_words


@pytest.fixture
def result():
    return extract_from_words(build_words(), filename="mandatory_insurance.pdf",
                              full_text="תעודת ביטוח חובה פקודת ביטוח רכב מנועי הראל")


def test_classified_as_mandatory_insurance():
    key, enum, conf = classify_document("תעודת ביטוח חובה פקודת ביטוח רכב מנועי", "")
    assert key == "mandatory_insurance"
    assert conf >= 0.7


def test_vehicle_number_is_7046676(result):
    f = result.fields.get("vehicle_number")
    assert f is not None, "vehicle_number was not extracted"
    assert f.value == "7046676"
    assert f.confidence >= 0.7
    assert "רישוי" in (f.label_detected or "")


def test_id_number_never_selected_as_vehicle_number(result):
    # The critical anti-confusion assertion.
    assert result.fields["vehicle_number"].value != "37005618"
    selected = [c for c in result.vehicle_candidates if c.selected]
    assert all(c.value != "37005618" for c in selected)


def test_id_number_extracted_correctly(result):
    assert result.field_value("id_number") == "37005618"


def test_policy_number_preserves_format(result):
    assert result.field_value("policy_number") == "201-502525667826-00"


def test_policy_holder(result):
    assert result.field_value("policy_holder") == "אבו עואד נדא"


def test_engine_and_year(result):
    assert result.field_value("engine_capacity") == "1197"
    assert result.field_value("production_year") == "2012"


def test_insurance_dates(result):
    assert result.field_value("insurance_start") == "2026-08-02"
    assert result.field_value("insurance_end") == "2026-08-15"


def test_insurance_type_mandatory(result):
    # mandatory maps to the COMPULSORY enum value.
    assert result.field_value("insurance_type") == "COMPULSORY"


def test_debug_candidates_present(result):
    values = {c.value for c in result.vehicle_candidates}
    assert "7046676" in values
    # ID appears as a candidate but with a negative score and not selected.
    id_cand = next((c for c in result.vehicle_candidates if c.value == "37005618"), None)
    assert id_cand is not None
    assert id_cand.score < result.fields["vehicle_number"].confidence * 180


def test_scoring_prefers_labelled_vehicle_number():
    words = build_words()[1]
    labels = find_label_hits(words)
    ranked = score_vehicle_candidates(words, labels)
    assert ranked[0].value == "7046676"
    assert ranked[0].selected is True


# --- Real-PDF regression (opt-in) ---------------------------------------------
# The actual certificate contains resident PII, so it is NOT committed. Drop it at
# tests/fixtures/mandatory_insurance_sample.pdf to run this test locally.
import os.path  # noqa: E402

_REAL_PDF = os.path.join(os.path.dirname(__file__), "fixtures", "mandatory_insurance_sample.pdf")


@pytest.mark.skipif(not os.path.exists(_REAL_PDF), reason="real sample PDF not present (PII, not committed)")
def test_real_pdf_vehicle_number():
    pytest.importorskip("pymupdf")
    from app.vehicles.extraction import extract_document

    r = extract_document(_REAL_PDF, "pdf")
    # Headline acceptance criterion.
    assert r.field_value("vehicle_number") == "7046676"
    assert r.fields["vehicle_number"].confidence >= 0.8  # auto-populates
    assert r.document_type == "COMPULSORY_INSURANCE"
    assert r.field_value("policy_number") == "201-502525667826-00"
    assert r.field_value("policy_holder") == "אבו עואד נדא"
    assert r.field_value("id_number") == "37005618"
    assert r.field_value("engine_capacity") == "1197"
    assert r.field_value("production_year") == "2012"
    assert r.field_value("insurance_start") == "2026-08-02"
    assert r.field_value("insurance_end") == "2026-08-15"
    assert r.field_value("premium") == "234.00"
    assert r.field_value("insurer") == "הפול"
    # The ID must NEVER be chosen as the vehicle number.
    assert r.field_value("vehicle_number") != "37005618"
    assert not any(c.value == "37005618" and c.selected for c in r.vehicle_candidates)
