from __future__ import annotations

from app.escalation.sanitizer import sanitize


def test_email_and_phone_and_id():
    r = sanitize("Contact dana@example.com or 050-123-4567, ID 123456789.")
    assert "[EMAIL]" in r.text
    assert "[PHONE]" in r.text
    assert "[ID]" in r.text
    assert "dana@example.com" not in r.text
    assert "123456789" not in r.text
    assert r.detected["email"] == 1
    assert r.sensitivity == "high"  # ID present


def test_vehicle_plate_not_treated_as_id():
    r = sanitize("Vehicle 12-345-67 needs service.")
    assert "[VEHICLE]" in r.text
    assert "12-345-67" not in r.text


def test_url_and_ip():
    r = sanitize("See https://internal.portal/secret at 10.0.0.5")
    assert "[URL]" in r.text
    assert "[IP]" in r.text


def test_clean_text_low_sensitivity():
    r = sanitize("When does the contract end and what are the terms?")
    assert r.detected == {}
    assert r.sensitivity == "low"
    assert r.text == "When does the contract end and what are the terms?"


def test_types_listing():
    r = sanitize("mail a@b.co phone 052-000-1111")
    assert set(r.types) == {"email", "phone"}
