"""Vehicle-registration-number candidate scoring (spec §12).

Never selects an arbitrary 7-8 digit number. A candidate is strongly rewarded for
being the value of a "מס' רישוי"-type label and strongly penalised for being the
value of ID / company / policy / agent labels, or for looking like a phone / year
/ money / date.
"""

from __future__ import annotations

from app.vehicles.extraction.layout import LabelHit, relation_score, resolve_value
from app.vehicles.extraction.normalizer import (
    digits_only,
    looks_like_date,
    looks_like_money,
    looks_like_phone,
    looks_like_year,
)
from app.vehicles.extraction.schemas import Candidate, Word

# Fields whose value must NOT be mistaken for the vehicle number.
_NEG_FIELDS = {
    "id_number": -100.0,
    "policy_number": -100.0,
    "agent_number": -80.0,
    "chassis": -60.0,
}
MIN_SELECT_SCORE = 60.0


def _claimed_tokens(labels: list[LabelHit], words: list[Word]) -> dict[int, tuple[str, float]]:
    """Map token id -> (field, penalty) for the resolved value of each negative
    label, so those tokens are penalised as vehicle-number candidates."""
    claimed: dict[int, tuple[str, float]] = {}
    for lab in labels:
        if lab.field not in _NEG_FIELDS:
            continue
        w, score, _rel = resolve_value(lab, words, numeric_only=True)
        if w is not None and score >= 45:
            claimed[id(w)] = (lab.field, _NEG_FIELDS[lab.field])
    return claimed


def score_vehicle_candidates(
    words: list[Word], labels: list[LabelHit]
) -> list[Candidate]:
    veh_labels = [h for h in labels if h.field == "vehicle_number"]
    claimed = _claimed_tokens(labels, words)

    # The vehicle label's own resolved value (strongest signal).
    veh_value_ids: set[int] = set()
    for lab in veh_labels:
        w, score, _ = resolve_value(lab, words, numeric_only=True)
        if w is not None and score >= 45:
            veh_value_ids.add(id(w))

    candidates: list[Candidate] = []
    for w in words:
        d = digits_only(w.text)
        if not (5 <= len(d) <= 10):
            continue

        score = 0.0
        reasons: list[str] = []
        label_txt: str | None = None

        if id(w) in veh_value_ids:
            score += 100
            reasons.append("value of vehicle-registration label")
            best_lab = max(veh_labels, key=lambda l: relation_score(l, w)[0], default=None)
            label_txt = best_lab.text if best_lab else None
        elif veh_labels:
            assoc = max(relation_score(l, w)[0] for l in veh_labels)
            score += min(assoc, 60) * 0.5
            if assoc >= 50:
                best_lab = max(veh_labels, key=lambda l: relation_score(l, w)[0])
                label_txt = best_lab.text
                reasons.append("near vehicle-registration label")

        if len(d) in (7, 8):
            score += 50
            reasons.append(f"{len(d)}-digit number")

        # Penalties.
        if id(w) in claimed:
            field, pen = claimed[id(w)]
            score += pen
            reasons.append(f"value of {field}")
            label_txt = label_txt or field
        if looks_like_phone(w.text):
            score -= 80
            reasons.append("looks like phone")
        if looks_like_year(w.text):
            score -= 50
            reasons.append("looks like year")
        if looks_like_money(w.text):
            score -= 50
            reasons.append("looks like money")
        if looks_like_date(w.text):
            score -= 50
            reasons.append("looks like date")

        candidates.append(Candidate(
            value=d, score=score, label=label_txt,
            reason="; ".join(reasons) or "numeric token", page=w.page,
        ))

    # Deduplicate identical values, keeping the highest score.
    best_by_value: dict[str, Candidate] = {}
    for c in candidates:
        cur = best_by_value.get(c.value)
        if cur is None or c.score > cur.score:
            best_by_value[c.value] = c
    ranked = sorted(best_by_value.values(), key=lambda c: c.score, reverse=True)

    if ranked and ranked[0].score >= MIN_SELECT_SCORE and len(ranked[0].value) in (7, 8):
        ranked[0].selected = True
    return ranked


def confidence_from_score(score: float) -> float:
    return max(0.0, min(0.99, score / 180.0))
