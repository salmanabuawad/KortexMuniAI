"""Password hashing (bcrypt directly).

We use the ``bcrypt`` library directly rather than passlib: passlib 1.7.x probes
its bcrypt backend with a >72-byte string, which bcrypt 4.1+ rejects, breaking
hashing at import time. bcrypt has a hard 72-byte limit, so we truncate on bytes
consistently for both hashing and verification.
"""

from __future__ import annotations

import bcrypt

_MAX = 72


def _prepare(plain: str) -> bytes:
    return plain.encode("utf-8")[:_MAX]


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(_prepare(plain), bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_prepare(plain), hashed.encode("ascii"))
    except (ValueError, TypeError):
        return False
