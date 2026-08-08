"""Deterministic insurance duplicate / overlap / redundancy engine.

CRITICAL ARCHITECTURE RULE (spec ADDITION): date overlap, duplicate detection,
expiry calculation and missing-coverage checks are pure Python business logic —
never delegated to the LLM. The LLM may *explain* a conflict, but this module
decides whether one exists.

All functions are side-effect free and operate on lightweight dataclasses so they
are trivial to unit-test without a database.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from app.models.enums import ConflictType, InsuranceType, Severity
from app.vehicles.normalization import normalize_registration

# A gap this small between an old policy ending and a new one starting is treated
# as a renewal, not a duplicate.
RENEWAL_GAP_DAYS = 31


@dataclass(frozen=True)
class PolicyLike:
    """Minimal policy shape the rules operate on."""

    id: str
    vehicle_number: str
    insurance_type: InsuranceType
    policy_number: str | None
    insurer: str | None
    start_date: date | None
    end_date: date | None
    file_hash: str | None = None


@dataclass(frozen=True)
class Conflict:
    policy_a_id: str
    policy_b_id: str
    conflict_type: ConflictType
    severity: Severity
    overlap_start: date | None
    overlap_end: date | None
    overlap_days: int
    message: str


def _overlap(a: PolicyLike, b: PolicyLike) -> tuple[date | None, date | None, int]:
    """Inclusive date-range overlap between two policies. Returns (start, end, days)."""
    if not (a.start_date and a.end_date and b.start_date and b.end_date):
        return None, None, 0
    start = max(a.start_date, b.start_date)
    end = min(a.end_date, b.end_date)
    if start > end:
        return None, None, 0
    return start, end, (end - start).days + 1


def _same_vehicle(a: PolicyLike, b: PolicyLike) -> bool:
    return normalize_registration(a.vehicle_number) == normalize_registration(b.vehicle_number)


def detect_conflict(a: PolicyLike, b: PolicyLike) -> Conflict | None:
    """Compare two policies for the same vehicle and classify any conflict.

    Precedence: exact duplicate > same-type overlap > comprehensive/third-party
    redundancy > likely renewal (informational).
    """
    if a.id == b.id or not _same_vehicle(a, b):
        return None

    # 1) Exact duplicate: identical file, or identical (policy number + insurer).
    if a.file_hash and b.file_hash and a.file_hash == b.file_hash:
        return Conflict(a.id, b.id, ConflictType.EXACT_DUPLICATE, Severity.HIGH,
                        None, None, 0, "Identical document uploaded more than once.")
    if (a.policy_number and a.policy_number == b.policy_number
            and (a.insurer or "").lower() == (b.insurer or "").lower()):
        return Conflict(a.id, b.id, ConflictType.EXACT_DUPLICATE, Severity.HIGH,
                        None, None, 0, "Same policy number and insurer.")

    o_start, o_end, o_days = _overlap(a, b)

    # 2) Same-type overlap (two comprehensive, or two compulsory, etc.).
    if a.insurance_type == b.insurance_type and o_days > 0:
        sev = Severity.HIGH if a.insurance_type in (
            InsuranceType.COMPREHENSIVE, InsuranceType.COMPULSORY) else Severity.WARNING
        return Conflict(a.id, b.id, ConflictType.OVERLAPPING_SAME_TYPE, sev,
                        o_start, o_end, o_days,
                        f"Two {a.insurance_type.value} policies overlap for {o_days} day(s).")

    # 3) Comprehensive + third-party redundancy (comprehensive usually includes 3rd-party).
    types = {a.insurance_type, b.insurance_type}
    if types == {InsuranceType.COMPREHENSIVE, InsuranceType.THIRD_PARTY} and o_days > 0:
        return Conflict(a.id, b.id, ConflictType.POTENTIAL_REDUNDANT_COVERAGE, Severity.WARNING,
                        o_start, o_end, o_days,
                        "Comprehensive and third-party coverage overlap — review for redundancy.")

    # 4) Likely renewal: same type, no overlap, new policy starts soon after old ends.
    if a.insurance_type == b.insurance_type and a.end_date and b.start_date:
        older, newer = (a, b) if a.end_date <= b.start_date else (b, a)
        if older.end_date and newer.start_date:
            gap = (newer.start_date - older.end_date).days
            if 0 <= gap <= RENEWAL_GAP_DAYS:
                return Conflict(older.id, newer.id, ConflictType.LIKELY_RENEWAL, Severity.INFO,
                                None, None, 0, f"Likely renewal (gap of {gap} day(s)).")
    return None


def find_conflicts(policies: list[PolicyLike]) -> list[Conflict]:
    """Pairwise scan of a vehicle's policies. O(n^2) — n is small per vehicle."""
    conflicts: list[Conflict] = []
    for i in range(len(policies)):
        for j in range(i + 1, len(policies)):
            c = detect_conflict(policies[i], policies[j])
            if c:
                conflicts.append(c)
    return conflicts


def days_until_expiry(end_date: date | None, today: date) -> int | None:
    if not end_date:
        return None
    return (end_date - today).days


def expiring_within(end_date: date | None, today: date, window_days: int) -> bool:
    d = days_until_expiry(end_date, today)
    return d is not None and 0 <= d <= window_days


def is_expired(end_date: date | None, today: date) -> bool:
    d = days_until_expiry(end_date, today)
    return d is not None and d < 0


@dataclass(frozen=True)
class DataQualityIssue:
    severity: Severity
    code: str
    message: str


def check_policy_quality(p: PolicyLike, *, selected_vehicle_number: str | None = None,
                         today: date | None = None) -> list[DataQualityIssue]:
    """Deterministic fraud / data-quality checks for a single policy."""
    issues: list[DataQualityIssue] = []
    if p.start_date and p.end_date and p.end_date < p.start_date:
        issues.append(DataQualityIssue(Severity.HIGH, "invalid_dates",
                                       "Policy end date is before its start date."))
    if not p.insurer:
        issues.append(DataQualityIssue(Severity.WARNING, "missing_insurer",
                                       "Insurer name is missing."))
    if not normalize_registration(p.vehicle_number):
        issues.append(DataQualityIssue(Severity.HIGH, "no_vehicle",
                                       "Document has no identifiable vehicle number."))
    if (selected_vehicle_number is not None
            and normalize_registration(selected_vehicle_number)
            and normalize_registration(p.vehicle_number) != normalize_registration(selected_vehicle_number)):
        issues.append(DataQualityIssue(Severity.CRITICAL, "vehicle_mismatch",
                                       "Document vehicle number differs from the selected vehicle."))
    if today and is_expired(p.end_date, today):
        issues.append(DataQualityIssue(Severity.INFO, "already_expired",
                                       "Extracted expiry date has already passed."))
    return issues
