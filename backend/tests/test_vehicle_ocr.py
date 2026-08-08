from __future__ import annotations

from app.models.enums import InsuranceType, VehicleDocumentType
from app.vehicles.ocr import classify_document, extract


def test_classify_comprehensive_hebrew():
    dt, conf = classify_document("ביטוח מקיף לרכב מספר 12-345-67")
    assert dt is VehicleDocumentType.COMPREHENSIVE_INSURANCE
    assert conf > 0.5


def test_extract_plate_and_type_and_dates():
    text = "ביטוח מקיף, רכב 12-345-67, הראל, מתאריך 01/01/2027 עד 31/12/2027, פוליסה 998877"
    ex = extract(text)
    assert ex.insurance_type is InsuranceType.COMPREHENSIVE
    assert ex.fields["registration_number"].value == "1234567"
    assert ex.fields["insurer"].value == "הראל"
    assert ex.fields["policy_number"].value == "998877"
    assert ex.fields["start_date"].value == "2027-01-01"
    assert ex.fields["end_date"].value == "2027-12-31"


def test_registration_document_classification():
    dt, _ = classify_document("רישיון רכב - משרד התחבורה")
    assert dt is VehicleDocumentType.VEHICLE_REGISTRATION
