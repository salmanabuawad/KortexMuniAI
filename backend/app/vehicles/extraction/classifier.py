"""Document-type classification (spec §3).

Different document types get different extractors — never one-size-fits-all parsing.
"""

from __future__ import annotations

from app.models.enums import VehicleDocumentType
from app.vehicles.extraction.anchors import DOC_TERMS

# Internal classifier key -> (enum, base confidence when matched).
_KEY_TO_ENUM: dict[str, VehicleDocumentType] = {
    "mandatory_insurance": VehicleDocumentType.COMPULSORY_INSURANCE,
    "third_party_insurance": VehicleDocumentType.THIRD_PARTY_INSURANCE,
    "comprehensive_insurance": VehicleDocumentType.COMPREHENSIVE_INSURANCE,
    "vehicle_registration": VehicleDocumentType.VEHICLE_REGISTRATION,
    "vehicle_test": VehicleDocumentType.VEHICLE_TEST,
    "protection_approval": VehicleDocumentType.PROTECTION_APPROVAL,
    "repair_invoice": VehicleDocumentType.MAINTENANCE_INVOICE,
    "warranty": VehicleDocumentType.WARRANTY,
}

# Priority order when several types match (insurance types first).
_PRIORITY = [
    "mandatory_insurance", "comprehensive_insurance", "third_party_insurance",
    "vehicle_registration", "protection_approval", "vehicle_test",
    "repair_invoice", "warranty",
]


def classify_document(text: str, filename: str = "") -> tuple[str, VehicleDocumentType, float]:
    """Return (key, enum, confidence)."""
    hay = f"{text}\n{filename}"
    scores: dict[str, int] = {}
    for key, terms in DOC_TERMS.items():
        hits = sum(1 for term in terms if term in hay)
        if hits:
            scores[key] = hits

    if not scores:
        return "unknown", VehicleDocumentType.UNKNOWN_VEHICLE_DOCUMENT, 0.3

    # Prefer strongest, breaking ties by priority order.
    def rank(k: str) -> tuple[int, int]:
        return (scores[k], -_PRIORITY.index(k) if k in _PRIORITY else -99)

    key = max(scores, key=rank)
    # Confidence grows with number of distinct anchor terms hit.
    conf = min(0.99, 0.7 + 0.1 * scores[key])
    return key, _KEY_TO_ENUM.get(key, VehicleDocumentType.UNKNOWN_VEHICLE_DOCUMENT), conf
