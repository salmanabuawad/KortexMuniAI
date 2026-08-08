from pathlib import Path

from app.rag.structured_qa import detect_field_intent, _format_value
from app.vehicles.extraction import extract_document

FIXTURE = Path(__file__).parent / "fixtures" / "mandatory_insurance_sample.pdf"


def test_detect_vehicle_number_intent_hebrew():
    assert detect_field_intent("מה מספר הרכב") == "vehicle_number"
    assert detect_field_intent("מה מס' רישוי?") == "vehicle_number"


def test_detect_vehicle_number_intent_arabic_and_english():
    assert detect_field_intent("ما رقم المركبة؟") == "vehicle_number"
    assert detect_field_intent("What is the vehicle registration number?") == "vehicle_number"


def test_other_structured_intents():
    assert detect_field_intent("מה מספר הפוליסה") == "policy_number"
    assert detect_field_intent("מתי פקיעת הביטוח?") == "insurance_end"
    assert detect_field_intent("מה נפח מנוע") == "engine_capacity"


def test_fixture_plate_is_ground_truth():
    result = extract_document(str(FIXTURE), "pdf")
    assert result.fields["vehicle_number"].value == "7046676"
    assert result.fields["vehicle_number"].confidence >= 0.70


def test_direct_answer_does_not_contain_nearby_engine_or_year_noise():
    answer = _format_value("vehicle_number", "7046676", "he")
    assert "7046676" in answer
    assert "1197" not in answer
    assert "2012" not in answer
    assert "8354" not in answer
