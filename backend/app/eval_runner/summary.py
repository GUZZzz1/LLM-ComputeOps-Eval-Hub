from __future__ import annotations

import json
from pathlib import Path

from backend.app.config import PROJECT_ROOT
from backend.app.db import get_connection


RUNS_DIR = PROJECT_ROOT / "runs"


def write_run_summary(run_id: str) -> dict:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                id AS run_id, model, case_file, concurrency, timeout_ms, retry_count,
                total_cases, success_count, failed_count, timeout_count,
                eval_pass_count, eval_fail_count, started_at, finished_at
            FROM eval_runs
            WHERE id = ?
            """,
            (run_id,),
        ).fetchone()

    if row is None:
        raise ValueError(f"Eval run not found: {run_id}")

    summary = dict(row)
    total_cases = int(summary.get("total_cases") or 0)
    request_failures = int(summary.get("failed_count") or 0) + int(
        summary.get("timeout_count") or 0
    )
    evaluated = int(summary.get("eval_pass_count") or 0) + int(
        summary.get("eval_fail_count") or 0
    )
    summary["request_error_rate"] = (
        request_failures / total_cases if total_cases > 0 else 0
    )
    summary["eval_pass_rate"] = (
        int(summary.get("eval_pass_count") or 0) / evaluated if evaluated > 0 else 0
    )

    output_dir = RUNS_DIR / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "run_summary.json"
    output_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary
