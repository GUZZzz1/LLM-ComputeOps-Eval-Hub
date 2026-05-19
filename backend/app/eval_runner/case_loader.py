from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from backend.app.config import PROJECT_ROOT
from backend.app.schemas import EvalCase


def resolve_case_file(case_file: str) -> Path:
    path = Path(case_file)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def load_eval_cases(case_file: str) -> list[EvalCase]:
    path = resolve_case_file(case_file)
    if not path.is_file():
        raise ValueError(f"Eval case file not found: {case_file}")

    cases: list[EvalCase] = []
    seen_ids: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            raw_line = line.strip()
            if not raw_line:
                continue
            try:
                payload = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSONL at {path}:{line_number}: {exc}"
                ) from exc

            try:
                case = EvalCase.model_validate(payload)
            except ValidationError as exc:
                raise ValueError(
                    f"Invalid eval case at {path}:{line_number}: {exc}"
                ) from exc

            if case.id in seen_ids:
                raise ValueError(f"Duplicate eval case id: {case.id}")
            seen_ids.add(case.id)
            cases.append(case)

    return cases
