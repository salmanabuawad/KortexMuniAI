"""Pydantic request/response schemas for the v1 API."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

# NOTE: email fields are plain ``str`` (not EmailStr) on purpose: MuniAI must
# support fully offline deployments where local ``*.local`` admin addresses are
# valid, but email-validator rejects such reserved-use domains.


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- auth ---
class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DepartmentOut(ORMModel):
    id: uuid.UUID
    name: str
    slug: str


class UserOut(ORMModel):
    id: uuid.UUID
    email: str
    full_name: str
    is_superuser: bool
    locale: str
    department: DepartmentOut | None = None
    permissions: list[str] = []


# --- agents ---
class AgentOut(ORMModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None = None
    icon: str | None = None
    enabled: bool


# --- documents ---
class DocumentOut(ORMModel):
    id: uuid.UUID
    title: str
    original_filename: str
    file_type: str | None = None
    classification: str
    language: str | None = None
    page_count: int | None = None
    processing_status: str
    indexing_status: str | None = None
    created_at: datetime


# --- chat ---
class ConversationCreate(BaseModel):
    title: str | None = None
    agent_id: uuid.UUID | None = None


class ConversationOut(ORMModel):
    id: uuid.UUID
    title: str
    agent_id: uuid.UUID | None = None
    pinned: bool
    archived: bool
    created_at: datetime
    updated_at: datetime


class MessageSourceOut(ORMModel):
    document_id: uuid.UUID | None = None
    document_title: str | None = None
    page: int | None = None
    snippet: str | None = None
    rank: int = 0


class MessageOut(ORMModel):
    id: uuid.UUID
    role: str
    content: str
    origin: str
    model: str | None = None
    provider: str | None = None
    confidence: float | None = None
    created_at: datetime
    sources: list[MessageSourceOut] = []


class ChatRequest(BaseModel):
    content: str
    agent_id: uuid.UUID | None = None
    document_id: uuid.UUID | None = None  # scope the answer to one chosen document


# --- vehicles ---
class VehicleOut(ORMModel):
    id: uuid.UUID
    registration_number: str
    normalized_number: str
    manufacturer: str | None = None
    model: str | None = None
    is_active: bool


class InsurancePolicyOut(ORMModel):
    id: uuid.UUID
    vehicle_id: uuid.UUID | None = None
    policy_number: str | None = None
    insurance_type: str
    insurer: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: str
    verified: bool


class ConflictOut(ORMModel):
    id: uuid.UUID
    vehicle_id: uuid.UUID | None = None
    policy_a_id: uuid.UUID | None = None
    policy_b_id: uuid.UUID | None = None
    conflict_type: str
    overlap_days: int | None = None
    severity: str
    status: str
    notes: str | None = None


class ExtractionOut(ORMModel):
    id: uuid.UUID
    field_name: str
    ocr_original_value: str | None = None
    corrected_value: str | None = None
    confidence: float | None = None
    verified: bool


class VehicleDocumentOut(ORMModel):
    id: uuid.UUID
    vehicle_id: uuid.UUID | None = None
    document_type: str
    original_filename: str
    review_status: str
    classification_confidence: float | None = None
    created_at: datetime


class ExtractionCorrection(BaseModel):
    field_name: str
    corrected_value: str


# --- global-AI escalation ---
class EscalationPrepareRequest(BaseModel):
    question: str
    context: str | None = None
    conversation_id: uuid.UUID | None = None


class EscalationPrepareResponse(BaseModel):
    escalation_id: uuid.UUID
    prompt: str
    detected_types: list[str] = []
    sensitivity: str


class EscalationImportRequest(BaseModel):
    conversation_id: uuid.UUID
    answer: str


# --- admin ---
class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class AdminUserCreate(BaseModel):
    email: str
    full_name: str
    password: str
    is_superuser: bool = False
    role_names: list[str] = []


class AuditOut(ORMModel):
    id: uuid.UUID
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    result: str
    detail: str | None = None
    created_at: datetime


class IntegrationOut(ORMModel):
    id: uuid.UUID
    name: str
    kind: str
    enabled: bool
    status: str


class AdminStats(BaseModel):
    users: int
    documents: int
    conversations: int
    vehicles: int
    conflicts: int


# --- health / meta ---
class ComponentHealth(BaseModel):
    name: str
    healthy: bool
    detail: str = ""


class HealthResponse(BaseModel):
    status: str
    version: str
    components: list[ComponentHealth]


class BrandingOut(BaseModel):
    org_name: str
    accent_color: str
    default_language: str
    languages: list[str] = ["he", "ar", "en"]
