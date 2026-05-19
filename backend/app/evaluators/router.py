from __future__ import annotations

from typing import Any

from backend.app.evaluators.answer_eval import AnswerEvaluator
from backend.app.evaluators.base import EvalOutcome
from backend.app.evaluators.format_eval import FormatEvaluator
from backend.app.evaluators.keyword_eval import KeywordEvaluator
from backend.app.evaluators.safety_eval import SafetyEvaluator
from backend.app.evaluators.tool_call_eval import ToolCallEvaluator


def evaluate_output(expected: dict[str, Any], output_text: str) -> EvalOutcome:
    expected_type = expected.get("type")
    evaluator = {
        "json_schema": FormatEvaluator(),
        "keyword": KeywordEvaluator(),
        "contains": AnswerEvaluator(),
        "exact": AnswerEvaluator(),
        "tool_call": ToolCallEvaluator(),
        "safety_refusal": SafetyEvaluator(),
    }.get(expected_type)

    if evaluator is None:
        return EvalOutcome(
            "unknown",
            False,
            0.0,
            f"Unsupported evaluator type: {expected_type}",
        )
    return evaluator.evaluate(expected, output_text)
