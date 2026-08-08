"""Runtime configuration stored in the DB (system_settings), layered over env.

Lets admins change AI behavior toggles at runtime without editing .env or
restarting. SECURITY: the OpenAI API key is NEVER stored here — it stays in the
server environment only. Only non-secret toggles live in the DB.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.system import SystemSetting

_KEY = "ai_config"

# Toggles that may be overridden at runtime (non-secret only).
_AI_KEYS = (
    "openai_enabled",
    "openai_escalation_mode",
    "local_confidence_threshold",
    "openai_model",
    "openai_redaction_enabled",
)


def get_ai_config(db: Session) -> dict:
    """Effective AI config: env defaults overlaid with DB overrides. Includes a
    derived ``openai_configured`` (enabled AND a key present in the environment)."""
    cfg = {
        "openai_enabled": settings.openai_enabled,
        "openai_escalation_mode": settings.openai_escalation_mode,
        "local_confidence_threshold": settings.local_confidence_threshold,
        "openai_model": settings.openai_model,
        "openai_redaction_enabled": settings.openai_redaction_enabled,
    }
    row = db.scalar(select(SystemSetting).where(SystemSetting.key == _KEY))
    if row and isinstance(row.value, dict):
        for k in _AI_KEYS:
            if row.value.get(k) is not None:
                cfg[k] = row.value[k]
    cfg["openai_configured"] = bool(cfg["openai_enabled"] and settings.openai_api_key.strip())
    return cfg


def set_ai_config(db: Session, updates: dict) -> dict:
    """Persist whitelisted toggle overrides. Ignores the API key and any unknown
    keys. Returns the new effective config."""
    row = db.scalar(select(SystemSetting).where(SystemSetting.key == _KEY))
    if not row:
        row = SystemSetting(key=_KEY, value={})
        db.add(row)
    value = dict(row.value or {})
    for k, v in (updates or {}).items():
        if k in _AI_KEYS:
            value[k] = v
    row.value = value  # reassign so SQLAlchemy tracks the JSON change
    db.commit()
    return get_ai_config(db)
