"""Deterministic insurance-rules engine tests (spec ADDITION).

These verify that overlap/duplicate/redundancy/renewal logic is correct WITHOUT
any LLM or database — the whole point of keeping this logic deterministic.
"""

from __future__ import annotations

from datetime import date

from app.models.enums import ConflictType, InsuranceType, Severity
from app.vehicles.insurance_rules import (
    PolicyLike,
    check_policy_quality,
    detect_conflict,
    expiring_within,
    find_conflicts,
    is_expired,
)


def _p(**kw) -> PolicyLike:
    base = dict(
        id="x", vehicle_number="12-345-67", insurance_type=InsuranceType.COMPREHENSIVE,
        policy_number=None, insurer="Insurer A",
        start_date=date(2027, 1, 1), end_date=date(2027, 12, 31), file_hash=None,
    )
    base.update(kw)
    return PolicyLike(**base)


def test_same_type_overlap_high_severity():
    a = _p(id="a", start_date=date(2027, 1, 1), end_date=date(2027, 12, 31))
    b = _p(id="b", insurer="Insurer B", start_date=date(2027, 6, 1), end_date=date(2028, 5, 31))
    c = detect_conflict(a, b)
    assert c is not None
    assert c.conflict_type is ConflictType.OVERLAPPING_SAME_TYPE
    assert c.severity is Severity.HIGH
    # 2027-06-01 .. 2027-12-31 inclusive = 214 days
    assert c.overlap_days == 214


def test_exact_duplicate_by_file_hash():
    a = _p(id="a", file_hash="deadbeef")
    b = _p(id="b", insurer="Other", file_hash="deadbeef")
    c = detect_conflict(a, b)
    assert c is not None and c.conflict_type is ConflictType.EXACT_DUPLICATE


def test_exact_duplicate_by_policy_number_and_insurer():
    a = _p(id="a", policy_number="POL-1", insurer="Insurer A")
    b = _p(id="b", policy_number="POL-1", insurer="insurer a")  # case-insensitive
    c = detect_conflict(a, b)
    assert c is not None and c.conflict_type is ConflictType.EXACT_DUPLICATE


def test_comprehensive_third_party_redundancy():
    a = _p(id="a", insurance_type=InsuranceType.COMPREHENSIVE)
    b = _p(id="b", insurance_type=InsuranceType.THIRD_PARTY)
    c = detect_conflict(a, b)
    assert c is not None
    assert c.conflict_type is ConflictType.POTENTIAL_REDUNDANT_COVERAGE
    assert c.severity is Severity.WARNING


def test_likely_renewal_not_flagged_as_duplicate():
    a = _p(id="a", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
    b = _p(id="b", insurer="Insurer B", start_date=date(2027, 1, 15), end_date=date(2027, 12, 31))
    c = detect_conflict(a, b)
    assert c is not None and c.conflict_type is ConflictType.LIKELY_RENEWAL


def test_different_vehicles_no_conflict():
    a = _p(id="a", vehicle_number="11-111-11")
    b = _p(id="b", vehicle_number="22-222-22")
    assert detect_conflict(a, b) is None


def test_normalized_vehicle_matching_across_formats():
    a = _p(id="a", vehicle_number="12345678", insurer="A")
    b = _p(id="b", vehicle_number="12-345-678", insurer="B",
           start_date=date(2027, 6, 1), end_date=date(2028, 5, 31))
    # Same normalized number -> overlap is detected.
    assert detect_conflict(a, b) is not None


def test_find_conflicts_pairwise():
    policies = [
        _p(id="a", start_date=date(2027, 1, 1), end_date=date(2027, 12, 31)),
        _p(id="b", insurer="B", start_date=date(2027, 6, 1), end_date=date(2028, 5, 31)),
        _p(id="c", vehicle_number="99-999-99"),
    ]
    conflicts = find_conflicts(policies)
    assert len(conflicts) == 1


def test_expiry_helpers():
    today = date(2027, 1, 1)
    assert expiring_within(date(2027, 1, 20), today, 30) is True
    assert expiring_within(date(2027, 3, 1), today, 30) is False
    assert is_expired(date(2026, 12, 1), today) is True


def test_quality_checks_flag_bad_dates_and_mismatch():
    p = _p(start_date=date(2027, 12, 31), end_date=date(2027, 1, 1), insurer=None)
    issues = {i.code for i in check_policy_quality(p, selected_vehicle_number="99-999-99")}
    assert "invalid_dates" in issues
    assert "missing_insurer" in issues
    assert "vehicle_mismatch" in issues
