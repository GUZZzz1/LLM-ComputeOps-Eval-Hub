from __future__ import annotations

import json
from typing import Any

from backend.app.evaluators.base import EvalOutcome


class FormatEvaluator:
    name = "format"

    def evaluate(self, expected: dict[str, Any], output_text: str) -> EvalOutcome:
        try:
            actual = json.loads(output_text)
        except json.JSONDecodeError as exc:
            return EvalOutcome(self.name, False, 0.0, f"JSON parse failed: {exc}")

        missing = [
            field for field in expected.get("required", []) if field not in actual
        ]
        if missing:
            return EvalOutcome(
                self.name, False, 0.0, f"Missing required fields: {', '.join(missing)}"
            )
        return EvalOutcome(self.name, True, 1.0, "JSON schema requirements matched")
