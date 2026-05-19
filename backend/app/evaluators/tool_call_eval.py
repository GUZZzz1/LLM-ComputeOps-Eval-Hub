from __future__ import annotations

import json
from typing import Any

from backend.app.evaluators.base import EvalOutcome


class ToolCallEvaluator:
    name = "tool_call"

    def evaluate(self, expected: dict[str, Any], output_text: str) -> EvalOutcome:
        try:
            actual = json.loads(output_text)
        except json.JSONDecodeError as exc:
            return EvalOutcome(self.name, False, 0.0, f"JSON parse failed: {exc}")

        actual_call = actual.get("tool_call", actual)
        actual_name = actual_call.get("tool_name") or actual_call.get("name")
        expected_name = expected.get("tool_name")
        if actual_name != expected_name:
            return EvalOutcome(
                self.name,
                False,
                0.0,
                f"Tool name mismatch: expected {expected_name}, got {actual_name}",
            )

        actual_params = actual_call.get("params", {})
        for key, value in expected.get("params", {}).items():
            if actual_params.get(key) != value:
                return EvalOutcome(
                    self.name,
                    False,
                    0.0,
                    f"Param mismatch for {key}: expected {value}, got {actual_params.get(key)}",
                )

        return EvalOutcome(self.name, True, 1.0, "Tool call matched")
