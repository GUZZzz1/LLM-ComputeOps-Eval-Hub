from __future__ import annotations

from typing import Any

from backend.app.evaluators.base import EvalOutcome


class KeywordEvaluator:
    name = "keyword"

    def evaluate(self, expected: dict[str, Any], output_text: str) -> EvalOutcome:
        keywords = [str(item) for item in expected.get("keywords", [])]
        match_mode = expected.get("match", "all")
        actual = output_text.lower()
        hits = [keyword for keyword in keywords if keyword.lower() in actual]

        if match_mode == "any":
            passed = bool(hits)
        else:
            passed = len(hits) == len(keywords)

        if passed:
            return EvalOutcome(self.name, True, 1.0, "Keyword requirements matched")
        return EvalOutcome(
            self.name,
            False,
            0.0,
            f"Keyword requirements not met; matched {len(hits)}/{len(keywords)}",
        )
