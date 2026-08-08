"""LLM provider abstraction (spec §5).

MuniAI must not be internally dependent on Ollama. New providers (vLLM, etc.)
must be pluggable without rewriting chat/RAG. Cloud providers are intentionally
NOT implemented — external AI is a manual, user-driven copy/paste escalation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field


@dataclass
class ChatMessage:
    role: str  # system | user | assistant
    content: str


@dataclass
class ChatResult:
    content: str
    model: str
    provider: str
    token_usage: dict = field(default_factory=dict)


@dataclass
class ProviderHealth:
    healthy: bool
    provider: str
    detail: str = ""
    models: list[str] = field(default_factory=list)


class LLMProvider(ABC):
    """Common interface every AI backend implements."""

    name: str = "base"

    @abstractmethod
    async def chat(
        self, messages: list[ChatMessage], *, model: str | None = None,
        temperature: float = 0.2, max_tokens: int | None = None,
    ) -> ChatResult: ...

    @abstractmethod
    def stream(
        self, messages: list[ChatMessage], *, model: str | None = None,
        temperature: float = 0.2, max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Yield content deltas as they are generated."""
        ...

    @abstractmethod
    async def embeddings(self, texts: list[str], *, model: str | None = None) -> list[list[float]]: ...

    @abstractmethod
    async def health(self) -> ProviderHealth: ...

    @abstractmethod
    async def models(self) -> list[str]: ...

    @abstractmethod
    async def model_info(self, model: str) -> dict: ...
