from __future__ import annotations

from typing import Any

from backend.app.evaluators.base import EvalOutcome


class AnswerEvaluator:
    name = "answer"

    def evaluate(self, expected: dict[str, Any], output_text: str) -> EvalOutcome:
        expected_type = expected.get("type")
        expected_text = str(expected.get("text", ""))

        if expected_type == "exact":
            passed = output_text.strip() == expected_text.strip()
            reason = "Exact answer matched" if passed else "Exact answer mismatch"
            return EvalOutcome(self.name, passed, 1.0 if passed else 0.0, reason)

        passed = expected_text in output_text
        reason = "Expected text found" if passed else "Expected text not found"
        return EvalOutcome(self.name, passed, 1.0 if passed else 0.0, reason)
