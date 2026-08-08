"""Provider registry / factory.

Selects the active provider from configuration. Architected so VLLMProvider (and
others) can register without touching chat/RAG code.
"""

from __future__ import annotations

from app.ai.base import LLMProvider
from app.ai.providers.ollama import OllamaProvider
from app.core.config import settings

_PROVIDERS: dict[str, type[LLMProvider]] = {
    "ollama": OllamaProvider,
    # "vllm": VLLMProvider,   # interface-for-later
}

_instance: LLMProvider | None = None


def get_provider() -> LLMProvider:
    global _instance
    if _instance is None:
        cls = _PROVIDERS.get(settings.ai_provider)
        if cls is None:
            raise ValueError(
                f"Unknown AI provider '{settings.ai_provider}'. "
                f"Available: {', '.join(_PROVIDERS)}"
            )
        _instance = cls()
    return _instance


def reset_provider() -> None:
    """Clear the cached provider (used by tests / config reloads)."""
    global _instance
    _instance = None
