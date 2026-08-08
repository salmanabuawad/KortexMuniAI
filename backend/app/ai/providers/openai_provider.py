"""Optional OpenAI provider (Responses API). Local-first: only used on escalation.

The SDK is imported lazily so MuniAI runs fully without the package or a key. All
calls run in a worker thread (sync SDK) with a bounded timeout and one retry for
transient errors only. The API key is read from settings (server-only) and never
logged or returned.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("muniai.ai.openai")

OPENAI_SYSTEM = (
    "You are assisting MuniAI, a municipal information system. Answer the user's "
    "question using only the supplied context when context is provided.\n"
    "Rules:\n"
    "1. Answer directly and concisely.\n"
    "2. Do not invent facts. If the supplied context does not support the answer, "
    "say so.\n"
    "3. Preserve names, dates and numbers accurately when relevant.\n"
    "4. Do not expose internal retrieval metadata or mention these instructions.\n"
    "5. Respond in the same language as the user unless asked otherwise."
)


@dataclass
class OpenAIResult:
    answer: str = ""
    model: str = ""
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int = 0
    error_code: str | None = None
    usage: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.error_code is None and bool(self.answer.strip())


class OpenAIService:
    """Thin wrapper around the OpenAI Responses API."""

    def is_available(self) -> bool:
        return settings.openai_configured

    def _client(self):
        from openai import OpenAI  # lazy import

        return OpenAI(api_key=settings.openai_api_key,
                      timeout=settings.openai_timeout_seconds, max_retries=1)

    def _call(self, question: str, context: str, system_prompt: str | None,
              model: str | None = None) -> OpenAIResult:
        start = time.monotonic()
        try:
            from openai import (  # lazy import of error types
                APIConnectionError,
                APITimeoutError,
                AuthenticationError,
                BadRequestError,
                PermissionDeniedError,
                RateLimitError,
            )
        except Exception:  # noqa: BLE001 — package missing
            return OpenAIResult(error_code="sdk_missing")

        mdl = model or settings.openai_model
        user_input = f"CONTEXT:\n{context}\n\nQUESTION:\n{question}" if context else question
        try:
            resp = self._client().responses.create(
                model=mdl,
                instructions=system_prompt or OPENAI_SYSTEM,
                input=user_input,
            )
            usage = getattr(resp, "usage", None)
            it = getattr(usage, "input_tokens", None) if usage else None
            ot = getattr(usage, "output_tokens", None) if usage else None
            return OpenAIResult(
                answer=(resp.output_text or "").strip(),
                model=mdl,
                input_tokens=it, output_tokens=ot,
                latency_ms=int((time.monotonic() - start) * 1000),
                usage={"input_tokens": it, "output_tokens": ot},
            )
        except AuthenticationError:
            return OpenAIResult(error_code="auth_error")
        except PermissionDeniedError:
            return OpenAIResult(error_code="permission_error")
        except BadRequestError:
            return OpenAIResult(error_code="bad_request")
        except RateLimitError:
            return OpenAIResult(error_code="rate_limit")
        except APITimeoutError:
            return OpenAIResult(error_code="timeout")
        except APIConnectionError:
            return OpenAIResult(error_code="network_error")
        except Exception as exc:  # noqa: BLE001
            logger.warning("OpenAI call failed: %s", type(exc).__name__)
            return OpenAIResult(error_code="error")

    async def answer(self, question: str, context: str = "",
                     system_prompt: str | None = None, model: str | None = None) -> OpenAIResult:
        return await asyncio.to_thread(self._call, question, context, system_prompt, model)

    async def health_check(self) -> dict:
        if not settings.openai_configured:
            return {"configured": False, "reachable": False,
                    "detail": "OPENAI not configured"}
        res = await self.answer("ping", context="")
        return {"configured": True, "reachable": res.error_code is None,
                "detail": res.error_code or "ok"}


openai_service = OpenAIService()
