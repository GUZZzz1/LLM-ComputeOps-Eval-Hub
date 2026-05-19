from __future__ import annotations

import json
from typing import Any

from backend.app.auth import now_iso
from backend.app.db import get_connection


def preview_text(value: str | None, limit: int = 500) -> str | None:
    if value is None:
        return None
    return value[:limit]


def messages_preview(messages: list[Any], limit: int = 500) -> str:
    parts: list[str] = []
    for message in messages:
        role = getattr(message, "role", "")
        content = getattr(message, "content", "")
        parts.append(f"{role}: {content}")
    return preview_text("\n".join(parts), limit) or ""


def create_request_log(
    *,
    request_id: str,
    user_id: str,
    api_key_id: str | None,
    provider: str,
    model: str,
    status: str,
    prompt_preview: str | None,
    output_preview: str | None,
    input_tokens: int | None,
    output_tokens: int | None,
    total_tokens: int | None,
    e2e_latency_ms: float | None,
    ttft_ms: float | None,
    tokens_per_second: float | None,
    error_type: str | None,
    error_message: str | None,
    metadata: dict[str, Any] | None,
) -> None:
    try:
        metadata_json = json.dumps(metadata or {}, ensure_ascii=False)
    except (TypeError, ValueError):
        metadata_json = "{}"

    safe_input_tokens = _non_negative_int(input_tokens)
    safe_output_tokens = _non_negative_int(output_tokens)
    safe_total_tokens = _non_negative_int(total_tokens)
    if safe_total_tokens < safe_input_tokens + safe_output_tokens:
        safe_total_tokens = safe_input_tokens + safe_output_tokens

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO request_logs (
                id, user_id, api_key_id, provider, model, status,
                prompt_preview, output_preview,
                input_tokens, output_tokens, total_tokens,
                e2e_latency_ms, ttft_ms, tokens_per_second,
                error_type, error_message, metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request_id,
                user_id,
                api_key_id,
                provider,
                model,
                status,
                preview_text(prompt_preview),
                preview_text(output_preview),
                safe_input_tokens,
                safe_output_tokens,
                safe_total_tokens,
                e2e_latency_ms,
                ttft_ms,
                max(0.0, float(tokens_per_second or 0)),
                error_type,
                preview_text(error_message, limit=1000),
                metadata_json,
                now_iso(),
            ),
        )
        conn.commit()


def _non_negative_int(value: int | None) -> int:
    if value is None:
        return 0
    return max(0, int(value))
