"""Pydantic request/response schemas for the v1 API."""

from __future__ import annotations

import uuid
from datetime import datetime

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
