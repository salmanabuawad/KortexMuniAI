"""Local filesystem storage for uploaded documents.

Content-addressed: files are stored under data/uploads/<sha256>. Identical
uploads reuse the same blob (spec §10 — do not store the same binary twice).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.core.config import settings


def _uploads_dir() -> Path:
    d = Path(settings.data_dir) / "uploads"
    d.mkdir(parents=True, exist_ok=True)
    return d


def compute_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def store_blob(data: bytes) -> tuple[str, str]:
    """Persist bytes content-addressed. Returns (sha256, absolute_path)."""
    digest = compute_hash(data)
    dest = _uploads_dir() / digest
    if not dest.exists():
        dest.write_bytes(data)
    return digest, str(dest)
