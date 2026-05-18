from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ProviderResponse:
    content: str | None
    raw_response: dict[str, Any] | None
    e2e_latency_ms: float | None
    input_tokens: int
    output_tokens: int
    total_tokens: int
    tokens_per_second: float | None
    error_type: str | None
    error_message: str | None
