"""Tests for the optional OpenAI escalation layer (spec §32/§33).

No real OpenAI calls — everything is exercised via the policy/redaction/provider
units. Routing that structured/local answers never trigger OpenAI is covered by
the policy + structured tests.
"""

from __future__ import annotations

import uuid

import pytest

from app.ai.policy import can_send_to_external_ai
from app.ai.providers.openai_provider import openai_service
from app.ai.redaction import blocked_category, redact
from app.core.config import settings
from app.models.iam import Permission, Role, User


def _user(*, escalation=True) -> User:
    role = Role(name="r")
    role.permissions = [Permission(action="GLOBAL_AI_ESCALATION", resource="*")] if escalation else []
    u = User(email="u@x", full_name="U")
    u.id = uuid.uuid4()
    u.roles = [role]
    return u


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setattr(settings, "openai_enabled", True)
    monkeypatch.setattr(settings, "openai_api_key", "sk-test-not-real")
    monkeypatch.setattr(settings, "openai_escalation_mode", "manual")


def test_denied_when_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "openai_enabled", False)
    d = can_send_to_external_ai(_user(), "hello")
    assert d.allowed is False and d.reason == "openai_not_configured"


def test_denied_when_disabled_mode(enabled, monkeypatch):
    monkeypatch.setattr(settings, "openai_escalation_mode", "disabled")
    assert can_send_to_external_ai(_user(), "hello").allowed is False


def test_denied_without_permission(enabled):
    d = can_send_to_external_ai(_user(escalation=False), "hello")
    assert d.allowed is False and d.reason == "user_not_permitted"


def test_denied_for_blocked_category(enabled):
    d = can_send_to_external_ai(_user(), "the admin password is hunter2")
    assert d.allowed is False and d.reason == "blocked_category"
    assert d.blocked_category == "password"


def test_allowed_when_configured_permitted_and_clean(enabled):
    d = can_send_to_external_ai(_user(), "מה התנאים לביטול הפוליסה?")
    assert d.allowed is True


def test_blocked_category_detects_api_key():
    assert blocked_category("here is sk-abcdef0123456789 token") is not None


def test_redaction_removes_pii(monkeypatch):
    monkeypatch.setattr(settings, "openai_redaction_enabled", True)
    text, detected = redact("אבו עואד נדא ת\"ז 37005618 טלפון 050-123-4567")
    assert "37005618" not in text
    assert "050-123-4567" not in text
    assert "id" in detected and "phone" in detected


def test_redaction_noop_when_disabled(monkeypatch):
    monkeypatch.setattr(settings, "openai_redaction_enabled", False)
    text, detected = redact("ת\"ז 37005618")
    assert text == "ת\"ז 37005618" and detected == []


def test_provider_availability(monkeypatch):
    monkeypatch.setattr(settings, "openai_enabled", False)
    assert openai_service.is_available() is False
    monkeypatch.setattr(settings, "openai_enabled", True)
    monkeypatch.setattr(settings, "openai_api_key", "sk-x")
    assert openai_service.is_available() is True


async def test_answer_fails_gracefully_without_valid_key(monkeypatch):
    # No real network/billing: with no valid key/SDK the call must not raise and
    # must report an error (local flow can then fall back).
    monkeypatch.setattr(settings, "openai_api_key", "")
    res = await openai_service.answer("hi", context="")
    assert res.ok is False
    assert res.error_code is not None
