"""RBAC permission-flattening tests (no DB required)."""

from __future__ import annotations

from app.models.iam import Permission, Role, User


def _user_with(*actions: str, superuser: bool = False) -> User:
    role = Role(name="r")
    role.permissions = [Permission(action=a, resource="*") for a in actions]
    u = User(email="u@x", full_name="U", is_superuser=superuser)
    u.roles = [role]
    return u


def test_permission_keys_from_roles():
    u = _user_with("VIEW", "AI_QUERY")
    assert u.permission_keys == {"VIEW:*", "AI_QUERY:*"}


def test_superuser_wildcard():
    u = _user_with(superuser=True)
    assert "*" in u.permission_keys


def test_user_without_roles_has_no_permissions():
    u = User(email="u@x", full_name="U")
    u.roles = []
    assert u.permission_keys == set()
