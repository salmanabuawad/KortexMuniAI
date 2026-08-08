"""Permission predicate tests (spec §55): a user must never see another user's
restricted document. Verifies the pure rule that mirrors the SQL retrieval filter."""

from __future__ import annotations

import uuid

from app.models.documents import Document
from app.models.enums import Classification
from app.models.iam import Role, User


def _user(dept=None, roles=(), superuser=False) -> User:
    u = User(email="u@x", full_name="U", is_superuser=superuser)
    u.id = uuid.uuid4()
    u.department_id = dept
    u.roles = list(roles)
    return u


def _doc(*, owner=None, dept=None, classification=Classification.INTERNAL) -> Document:
    d = Document(title="d", original_filename="d", content_hash="h",
                 classification=classification)
    d.id = uuid.uuid4()
    d.owner_id = owner
    d.department_id = dept
    return d


def test_owner_can_access_own_restricted_doc():
    from app.rag.access import can_access
    u = _user()
    d = _doc(owner=u.id, classification=Classification.RESTRICTED)
    assert can_access(u, d) is True


def test_other_user_cannot_access_restricted_doc():
    from app.rag.access import can_access
    owner = _user()
    other = _user()
    d = _doc(owner=owner.id, classification=Classification.CONFIDENTIAL)
    assert can_access(other, d) is False


def test_public_doc_visible_to_all():
    from app.rag.access import can_access
    assert can_access(_user(), _doc(classification=Classification.PUBLIC)) is True


def test_same_department_internal_access():
    from app.rag.access import can_access
    dept = uuid.uuid4()
    assert can_access(_user(dept=dept), _doc(dept=dept)) is True


def test_different_department_denied():
    from app.rag.access import can_access
    assert can_access(_user(dept=uuid.uuid4()), _doc(dept=uuid.uuid4())) is False


def test_explicit_role_grant():
    from app.rag.access import can_access
    role = Role(name="finance")
    role.id = uuid.uuid4()
    u = _user(roles=[role])
    d = _doc(classification=Classification.CONFIDENTIAL)
    assert can_access(u, d, grant_keys={f"role:{role.id}"}) is True


def test_superuser_sees_everything():
    from app.rag.access import can_access
    assert can_access(_user(superuser=True), _doc(classification=Classification.RESTRICTED)) is True
