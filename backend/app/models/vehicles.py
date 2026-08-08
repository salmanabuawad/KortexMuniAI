"""Vehicle-document intelligence module (spec ADDITION).

Design rule: OCR/classification may use AI, but duplicate/overlap/expiry logic is
**deterministic Python business logic** — the LLM is never the source of truth for
date math (see app/vehicles/insurance_rules.py).

Per-field extraction stores value + confidence + verification, and never
overwrites extraction history (OCR_ORIGINAL_VALUE vs CORRECTED_VALUE).
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import (
    Boolean,
    Date,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import (
    ConflictType,
    InsuranceType,
    PolicyStatus,
    Severity,
    VehicleDocumentType,
)


class Vehicle(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "vehicles"

    # normalized_number is the canonical form used for matching (digits only).
    registration_number: Mapped[str] = mapped_column(String(40), nullable=False)
    normalized_number: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    manufacturer: Mapped[str | None] = mapped_column(String(120))
    model: Mapped[str | None] = mapped_column(String(120))
    year: Mapped[int | None] = mapped_column(Integer)
    vehicle_type: Mapped[str | None] = mapped_column(String(80))
    vin: Mapped[str | None] = mapped_column(String(60))
    fuel_type: Mapped[str | None] = mapped_column(String(40))
    color: Mapped[str | None] = mapped_column(String(40))
    gross_weight: Mapped[str | None] = mapped_column(String(40))
    registration_expiry: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL")
    )

    documents: Mapped[list["VehicleDocument"]] = relationship(back_populates="vehicle")
    policies: Mapped[list["InsurancePolicy"]] = relationship(back_populates="vehicle")


class VehicleDocument(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "vehicle_documents"

    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vehicles.id", ondelete="SET NULL"), index=True
    )
    document_type: Mapped[VehicleDocumentType] = mapped_column(
        String(40), default=VehicleDocumentType.UNKNOWN_VEHICLE_DOCUMENT, nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_path: Mapped[str | None] = mapped_column(String(1000))
    content_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(120))
    page_count: Mapped[int | None] = mapped_column(Integer)

    ocr_text: Mapped[str | None] = mapped_column(Text)  # original OCR text, retained
    classification_confidence: Mapped[float | None] = mapped_column(Float)
    review_status: Mapped[str] = mapped_column(String(30), default="needs_review")
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    vehicle: Mapped[Vehicle | None] = relationship(back_populates="documents")
    extractions: Mapped[list["VehicleDocumentExtraction"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class VehicleDocumentVersion(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "vehicle_document_versions"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vehicle_documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    storage_path: Mapped[str | None] = mapped_column(String(1000))
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class VehicleDocumentExtraction(UUIDMixin, TimestampMixin, Base):
    """One extracted field with confidence + verification + correction history."""

    __tablename__ = "vehicle_document_extractions"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vehicle_documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    field_name: Mapped[str] = mapped_column(String(80), nullable=False)
    ocr_original_value: Mapped[str | None] = mapped_column(Text)
    corrected_value: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
    source_page: Mapped[int | None] = mapped_column(Integer)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    verified_at: Mapped[Date | None] = mapped_column(Date)

    document: Mapped[VehicleDocument] = relationship(back_populates="extractions")

    @property
    def value(self) -> str | None:
        """The authoritative value: user correction wins over OCR."""
        return self.corrected_value if self.corrected_value is not None else self.ocr_original_value


class InsurancePolicy(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "insurance_policies"

    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vehicles.id", ondelete="SET NULL"), index=True
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vehicle_documents.id", ondelete="SET NULL")
    )
    policy_number: Mapped[str | None] = mapped_column(String(120), index=True)
    insurance_type: Mapped[InsuranceType] = mapped_column(String(20), nullable=False)
    insurer: Mapped[str | None] = mapped_column(String(200))
    agent: Mapped[str | None] = mapped_column(String(200))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    insured_party: Mapped[str | None] = mapped_column(String(200))
    premium: Mapped[float | None] = mapped_column(Numeric(12, 2))
    deductible: Mapped[float | None] = mapped_column(Numeric(12, 2))
    coverage_json: Mapped[dict] = mapped_column(JSON, default=dict)
    protection_requirements: Mapped[str | None] = mapped_column(Text)
    status: Mapped[PolicyStatus] = mapped_column(String(30), default=PolicyStatus.NEEDS_REVIEW)
    confidence: Mapped[float | None] = mapped_column(Float)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    vehicle: Mapped[Vehicle | None] = relationship(back_populates="policies")


class InsuranceConflict(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "insurance_conflicts"

    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), index=True
    )
    policy_a_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("insurance_policies.id", ondelete="CASCADE")
    )
    policy_b_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("insurance_policies.id", ondelete="CASCADE")
    )
    conflict_type: Mapped[ConflictType] = mapped_column(String(40), nullable=False)
    overlap_start: Mapped[date | None] = mapped_column(Date)
    overlap_end: Mapped[date | None] = mapped_column(Date)
    overlap_days: Mapped[int | None] = mapped_column(Integer)
    severity: Mapped[Severity] = mapped_column(String(20), default=Severity.WARNING)
    status: Mapped[str] = mapped_column(String(30), default="needs_review")
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[Date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)


class VehicleComplianceRule(UUIDMixin, TimestampMixin, Base):
    """Configurable per-municipality rules (do not hard-code council policy)."""

    __tablename__ = "vehicle_compliance_rules"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    rule_json: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class VehicleAlert(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "vehicle_alerts"

    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(80), nullable=False)  # expiry|missing|conflict|fraud
    severity: Mapped[Severity] = mapped_column(String(20), default=Severity.WARNING)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
