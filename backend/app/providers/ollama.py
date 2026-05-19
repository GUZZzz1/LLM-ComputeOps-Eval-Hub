from __future__ import annotations

import time

import httpx
from json import JSONDecodeError

from backend.app.config import settings
from backend.app.providers.base import ProviderResponse
from backend.app.schemas import ChatMessage


class OllamaProvider:
    provider = "ollama"

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")

    async def chat(
        self,
        model: str,
        messages: list[ChatMessage],
        temperature: float | None,
        max_tokens: int | None,
    ) -> ProviderResponse:
        input_tokens = self._estimate_input_tokens(messages)
        payload = {
            "model": model,
            "messages": [message.dict() for message in messages],
            "stream": False,
            "options": {
                "temperature": temperature if temperature is not None else 0.7,
                "num_predict": max_tokens if max_tokens is not None else 256,
            },
        }

        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
            elapsed_ms = (time.perf_counter() - started) * 1000

            if response.status_code >= 400:
                return ProviderResponse(
                    content=None,
                    raw_response=self._safe_json(response),
                    e2e_latency_ms=elapsed_ms,
                    input_tokens=input_tokens,
                    output_tokens=0,
                    total_tokens=input_tokens,
                    tokens_per_second=0,
                    error_type="provider_error",
                    error_message=f"Ollama returned HTTP {response.status_code}: {response.text}",
                )

            try:
                raw = response.json()
            except JSONDecodeError as exc:
                return ProviderResponse(
                    content=None,
                    raw_response=None,
                    e2e_latency_ms=elapsed_ms,
                    input_tokens=input_tokens,
                    output_tokens=0,
                    total_tokens=input_tokens,
                    tokens_per_second=0,
                    error_type="provider_error",
                    error_message=f"Ollama returned invalid JSON: {exc}",
                )

            content = (raw.get("message") or {}).get("content") or ""
            output_tokens = max(0, len(content) // 2)
            total_tokens = input_tokens + output_tokens
            seconds = elapsed_ms / 1000
            tokens_per_second = output_tokens / seconds if seconds > 0 else 0

            return ProviderResponse(
                content=content,
                raw_response=raw,
                e2e_latency_ms=elapsed_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                tokens_per_second=tokens_per_second,
                error_type=None,
                error_message=None,
            )
        except httpx.TimeoutException as exc:
            elapsed_ms = (time.perf_counter() - started) * 1000
            return ProviderResponse(
                content=None,
                raw_response=None,
                e2e_latency_ms=elapsed_ms,
                input_tokens=input_tokens,
                output_tokens=0,
                total_tokens=input_tokens,
                tokens_per_second=0,
                error_type="timeout",
                error_message=str(exc) or "Ollama request timed out",
            )
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - started) * 1000
            return ProviderResponse(
                content=None,
                raw_response=None,
                e2e_latency_ms=elapsed_ms,
                input_tokens=input_tokens,
                output_tokens=0,
                total_tokens=input_tokens,
                tokens_per_second=0,
                error_type="provider_error",
                error_message=str(exc),
            )

    @staticmethod
    def _estimate_input_tokens(messages: list[ChatMessage]) -> int:
        total_chars = sum(len(message.content) for message in messages)
        return max(0, total_chars // 2)

    @staticmethod
    def _safe_json(response: httpx.Response) -> dict | None:
        try:
            return response.json()
        except Exception:
            return None
