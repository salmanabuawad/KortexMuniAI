"""Application configuration.

All settings are loaded from environment variables (prefix ``MUNIAI_``) or, in
development, from a local ``.env`` file. In production the canonical source is
``/etc/muniai/muniai.env`` loaded by the systemd unit.

Local-first policy: there are intentionally **no** cloud AI API keys here. The
system must run fully without ``OPENAI_API_KEY`` / ``ANTHROPIC_API_KEY`` / etc.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MUNIAI_",
        env_file=(".env",),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Core ---
    env: str = "development"
    secret_key: str = "change-me"
    base_url: str = "http://localhost:5173"
    log_level: str = "INFO"

    # --- API ---
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173"

    # --- Auth ---
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    bootstrap_admin_email: str = "admin@muniai.local"
    bootstrap_admin_password: str = "ChangeMe!123"
    bootstrap_admin_name: str = "System Administrator"

    # --- Database ---
    database_url: str = "postgresql+psycopg://muniai:muniai@localhost:5432/muniai"

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"

    # --- AI (local-first) ---
    ai_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "llama3.1:8b"
    ollama_embed_model: str = "nomic-embed-text"
    ollama_timeout_seconds: int = 120

    # --- OpenAI (OPTIONAL external escalation; local stays default) ---
    openai_enabled: bool = False
    openai_api_key: str = ""            # backend-only; never sent to the frontend
    openai_model: str = "gpt-4o-mini"
    openai_escalation_mode: str = "manual"   # manual | automatic | disabled
    openai_timeout_seconds: int = 30
    local_confidence_threshold: float = 0.65
    openai_max_context_chars: int = 12000
    openai_redaction_enabled: bool = True
    # Never sent externally even if requested (comma-separated).
    external_ai_blocked_categories: str = "password,token,api_key,credential,secret"

    # --- Localization ---
    default_language: str = "he"
    default_timezone: str = "Asia/Jerusalem"

    # --- Storage ---
    data_dir: Path = Path("/opt/muniai/data")
    max_upload_mb: int = 200

    # --- Branding ---
    org_name: str = "MuniAI"
    org_accent_color: str = "#0F6CBD"

    @field_validator("cors_origins")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def openai_configured(self) -> bool:
        return self.openai_enabled and bool(self.openai_api_key.strip())

    @property
    def blocked_categories(self) -> list[str]:
        return [c.strip().lower() for c in self.external_ai_blocked_categories.split(",") if c.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
