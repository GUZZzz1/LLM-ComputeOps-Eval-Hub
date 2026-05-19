from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class EvalOutcome:
    evaluator_name: str
    passed: bool
    score: float
    reason: str


class Evaluator(Protocol):
    name: str

    def evaluate(self, expected: dict[str, Any], output_text: str) -> EvalOutcome:
        ...
