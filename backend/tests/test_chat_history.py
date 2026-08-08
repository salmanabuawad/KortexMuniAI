"""Regression: _build_history must tolerate enum columns reloaded as plain strings.

On the second message in a conversation, Message.role comes back from the DB as a
str (the column is stored as String), which previously crashed on m.role.value and
surfaced as a bogus "AI unavailable" error in the UI.
"""

from __future__ import annotations

from types import SimpleNamespace

from app.api.v1.chat import _build_history
from app.models.enums import MessageRole


def _msg(role, content):
    return SimpleNamespace(role=role, content=content)


def test_build_history_with_string_roles():
    convo = SimpleNamespace(messages=[
        _msg("user", "first question"),
        _msg("assistant", "first answer"),
        _msg("user", "follow up"),
    ])
    history = _build_history(convo, None)
    roles = [h.role for h in history]
    assert roles[0] == "system"
    assert roles[1:] == ["user", "assistant", "user"]


def test_build_history_with_enum_roles():
    convo = SimpleNamespace(messages=[
        _msg(MessageRole.USER, "hi"),
        _msg(MessageRole.ASSISTANT, "hello"),
    ])
    history = _build_history(convo, None)
    assert [h.role for h in history][1:] == ["user", "assistant"]


def test_build_history_skips_system_rows():
    convo = SimpleNamespace(messages=[_msg("system", "ignored"), _msg("user", "q")])
    history = _build_history(convo, None)
    assert [h.role for h in history] == ["system", "user"]
