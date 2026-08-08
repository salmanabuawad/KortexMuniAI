"""Ollama local LLM provider.

Talks to a locally running Ollama server (default http://localhost:11434). No
data leaves the machine. Uses the streaming /api/chat and /api/embeddings routes.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from app.ai.base import ChatMessage, ChatResult, LLMProvider, ProviderHealth
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("muniai.ai.ollama")


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(
        self,
        base_url: str | None = None,
        chat_model: str | None = None,
        embed_model: str | None = None,
        timeout: int | None = None,
    ):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.chat_model = chat_model or settings.ollama_chat_model
        self.embed_model = embed_model or settings.ollama_embed_model
        self.timeout = timeout or settings.ollama_timeout_seconds

    def _payload(self, messages, model, temperature, max_tokens, stream: bool) -> dict:
        options: dict = {"temperature": temperature}
        if max_tokens:
            options["num_predict"] = max_tokens
        return {
            "model": model or self.chat_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": stream,
            "options": options,
        }

    async def chat(
        self, messages: list[ChatMessage], *, model=None, temperature=0.2, max_tokens=None,
    ) -> ChatResult:
        payload = self._payload(messages, model, temperature, max_tokens, stream=False)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
        return ChatResult(
            content=data.get("message", {}).get("content", ""),
            model=payload["model"],
            provider=self.name,
            token_usage={
                "prompt": data.get("prompt_eval_count"),
                "completion": data.get("eval_count"),
            },
        )

    async def stream(
        self, messages: list[ChatMessage], *, model=None, temperature=0.2, max_tokens=None,
    ) -> AsyncIterator[str]:
        payload = self._payload(messages, model, temperature, max_tokens, stream=True)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    delta = chunk.get("message", {}).get("content")
                    if delta:
                        yield delta
                    if chunk.get("done"):
                        break

    async def embeddings(self, texts: list[str], *, model=None) -> list[list[float]]:
        model = model or self.embed_model
        vectors: list[list[float]] = []
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for text in texts:
                resp = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": model, "prompt": text},
                )
                resp.raise_for_status()
                vectors.append(resp.json().get("embedding", []))
        return vectors

    async def health(self) -> ProviderHealth:
        try:
            models = await self.models()
            return ProviderHealth(True, self.name, "ok", models)
        except Exception as exc:  # noqa: BLE001 — health check must not raise
            logger.warning("Ollama health check failed: %s", exc)
            return ProviderHealth(False, self.name, str(exc))

    async def models(self) -> list[str]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}/api/tags")
            resp.raise_for_status()
            return [m["name"] for m in resp.json().get("models", [])]

    async def model_info(self, model: str) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.base_url}/api/show", json={"name": model})
            resp.raise_for_status()
            return resp.json()
