from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass

from backend.app.auth import new_id, now_iso
from backend.app.db import get_connection
from backend.app.eval_runner.case_loader import load_eval_cases
from backend.app.eval_runner import summary
from backend.app.evaluators.base import EvalOutcome
from backend.app.evaluators.router import evaluate_output
from backend.app.providers.base import ProviderResponse
from backend.app.providers.ollama import OllamaProvider
from backend.app.schemas import EvalCase
from backend.app.services.request_logger import create_request_log, preview_text


@dataclass
class TaskOutcome:
    task_id: str
    request_log_id: str | None
    status: str
    retry_times: int
    output_text: str | None
    error_type: str | None
    error_message: str | None
    e2e_latency_ms: float | None
    input_tokens: int
    output_tokens: int
    total_tokens: int
    tokens_per_second: float
    eval_outcome: EvalOutcome


class EvalRunner:
    provider_name = "ollama"

    async def run(
        self,
        *,
        user_id: str,
        model: str,
        case_file: str,
        concurrency: int,
        timeout_ms: int,
        retry_count: int,
        name: str | None = None,
    ) -> dict:
        if _get_active_model(model) is None:
            raise ValueError(f"Model is not active or does not exist: {model}")

        cases = load_eval_cases(case_file)
        run_id = new_id("run")
        now = now_iso()

        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO eval_runs (
                    id, user_id, name, provider, model, case_file, concurrency,
                    timeout_ms, retry_count, status, total_cases, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                """,
                (
                    run_id,
                    user_id,
                    name,
                    self.provider_name,
                    model,
                    case_file,
                    concurrency,
                    timeout_ms,
                    retry_count,
                    len(cases),
                    now,
                ),
            )
            for case in cases:
                conn.execute(
                    """
                    INSERT INTO eval_tasks (
                        id, run_id, case_id, category, prompt, expected_json,
                        status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
                    """,
                    (
                        new_id("task"),
                        run_id,
                        case.id,
                        case.category,
                        case.prompt,
                        json.dumps(case.expected, ensure_ascii=False),
                        now_iso(),
                    ),
                )
            conn.commit()

        started_at = now_iso()
        _update_run_status(run_id, "running", started_at=started_at)
        semaphore = asyncio.Semaphore(concurrency)
        await asyncio.gather(
            *[
                self._run_one_case(
                    semaphore=semaphore,
                    run_id=run_id,
                    user_id=user_id,
                    model=model,
                    case=case,
                    timeout_ms=timeout_ms,
                    retry_count=retry_count,
                )
                for case in cases
            ]
        )

        finished_at = now_iso()
        counts = _collect_counts(run_id)
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE eval_runs
                SET status = 'finished',
                    success_count = ?,
                    failed_count = ?,
                    timeout_count = ?,
                    eval_pass_count = ?,
                    eval_fail_count = ?,
                    finished_at = ?
                WHERE id = ?
                """,
                (
                    counts["success_count"],
                    counts["failed_count"],
                    counts["timeout_count"],
                    counts["eval_pass_count"],
                    counts["eval_fail_count"],
                    finished_at,
                    run_id,
                ),
            )
            conn.commit()

        run_summary = summary.write_run_summary(run_id)
        return {"run_id": run_id, "status": "finished", "summary": run_summary}

    async def _run_one_case(
        self,
        *,
        semaphore: asyncio.Semaphore,
        run_id: str,
        user_id: str,
        model: str,
        case: EvalCase,
        timeout_ms: int,
        retry_count: int,
    ) -> None:
        async with semaphore:
            task_id = _get_task_id(run_id, case.id)
            _mark_task_running(task_id)
            outcome = await self._execute_with_retry(
                run_id=run_id,
                user_id=user_id,
                model=model,
                case=case,
                task_id=task_id,
                timeout_ms=timeout_ms,
                retry_count=retry_count,
            )
            _finish_task(outcome)
            _write_eval_result(
                run_id=run_id,
                task_id=task_id,
                case=case,
                outcome=outcome,
            )

    async def _execute_with_retry(
        self,
        *,
        run_id: str,
        user_id: str,
        model: str,
        case: EvalCase,
        task_id: str,
        timeout_ms: int,
        retry_count: int,
    ) -> TaskOutcome:
        last_outcome: TaskOutcome | None = None
        for attempt in range(retry_count + 1):
            request_id = new_id("req")
            try:
                result = await asyncio.wait_for(
                    OllamaProvider().chat(
                        model=model,
                        messages=[_Message(role="user", content=case.prompt)],
                        temperature=0.2,
                        max_tokens=512,
                    ),
                    timeout=timeout_ms / 1000,
                )
            except asyncio.TimeoutError:
                result = ProviderResponse(
                    content=None,
                    raw_response=None,
                    e2e_latency_ms=float(timeout_ms),
                    input_tokens=max(0, len(case.prompt) // 2),
                    output_tokens=0,
                    total_tokens=max(0, len(case.prompt) // 2),
                    tokens_per_second=0,
                    error_type="timeout",
                    error_message=f"Eval task timed out after {timeout_ms} ms",
                )

            last_outcome = _outcome_from_provider_response(
                request_id=request_id,
                run_id=run_id,
                user_id=user_id,
                model=model,
                case=case,
                task_id=task_id,
                retry_times=attempt,
                result=result,
            )
            if last_outcome.status == "success":
                return last_outcome

        assert last_outcome is not None
        return last_outcome


@dataclass
class _Message:
    role: str
    content: str

    def dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


def _outcome_from_provider_response(
    *,
    request_id: str,
    run_id: str,
    user_id: str,
    model: str,
    case: EvalCase,
    task_id: str,
    retry_times: int,
    result: ProviderResponse,
) -> TaskOutcome:
    output_text = result.content or ""
    status = "success"
    error_type = result.error_type
    error_message = result.error_message
    if result.error_type == "timeout":
        status = "timeout"
    elif result.error_type:
        status = "failed"

    metadata = {
        **case.metadata,
        "eval_run_id": run_id,
        "eval_task_id": task_id,
        "eval_case_id": case.id,
    }
    create_request_log(
        request_id=request_id,
        user_id=user_id,
        api_key_id=None,
        provider="ollama",
        model=model,
        status="success" if status == "success" else "failed",
        prompt_preview=preview_text(f"user: {case.prompt}"),
        output_preview=preview_text(output_text) if status == "success" else None,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        total_tokens=result.total_tokens,
        e2e_latency_ms=result.e2e_latency_ms,
        ttft_ms=None,
        tokens_per_second=result.tokens_per_second,
        error_type=error_type,
        error_message=error_message,
        metadata=metadata,
    )

    if status == "success":
        eval_outcome = evaluate_output(case.expected, output_text)
    else:
        eval_outcome = EvalOutcome(
            "task_error",
            False,
            0.0,
            error_message or error_type or "Model request failed",
        )

    return TaskOutcome(
        task_id=task_id,
        request_log_id=request_id,
        status=status,
        retry_times=retry_times,
        output_text=output_text if status == "success" else None,
        error_type=error_type,
        error_message=error_message,
        e2e_latency_ms=result.e2e_latency_ms,
        input_tokens=max(0, int(result.input_tokens or 0)),
        output_tokens=max(0, int(result.output_tokens or 0)),
        total_tokens=max(0, int(result.total_tokens or 0)),
        tokens_per_second=max(0.0, float(result.tokens_per_second or 0)),
        eval_outcome=eval_outcome,
    )


def _get_active_model(model_name: str):
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT provider, model_name, display_name
            FROM models
            WHERE model_name = ? AND is_active = 1
            """,
            (model_name,),
        ).fetchone()


def _update_run_status(
    run_id: str, status: str, *, started_at: str | None = None
) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE eval_runs SET status = ?, started_at = COALESCE(?, started_at) WHERE id = ?",
            (status, started_at, run_id),
        )
        conn.commit()


def _get_task_id(run_id: str, case_id: str) -> str:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM eval_tasks WHERE run_id = ? AND case_id = ?",
            (run_id, case_id),
        ).fetchone()
    if row is None:
        raise ValueError(f"Eval task not found for case {case_id}")
    return row["id"]


def _mark_task_running(task_id: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE eval_tasks SET status = 'running', started_at = ? WHERE id = ?",
            (now_iso(), task_id),
        )
        conn.commit()


def _finish_task(outcome: TaskOutcome) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE eval_tasks
            SET status = ?, request_log_id = ?, retry_times = ?, output_text = ?,
                error_type = ?, error_message = ?, e2e_latency_ms = ?,
                input_tokens = ?, output_tokens = ?, total_tokens = ?,
                tokens_per_second = ?, finished_at = ?
            WHERE id = ?
            """,
            (
                outcome.status,
                outcome.request_log_id,
                outcome.retry_times,
                preview_text(outcome.output_text, limit=2000),
                outcome.error_type,
                outcome.error_message,
                outcome.e2e_latency_ms,
                outcome.input_tokens,
                outcome.output_tokens,
                outcome.total_tokens,
                outcome.tokens_per_second,
                now_iso(),
                outcome.task_id,
            ),
        )
        conn.commit()


def _write_eval_result(
    *, run_id: str, task_id: str, case: EvalCase, outcome: TaskOutcome
) -> None:
    result = outcome.eval_outcome
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO eval_results (
                id, run_id, task_id, case_id, evaluator_name, passed, score,
                reason, expected_json, actual_text, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("result"),
                run_id,
                task_id,
                case.id,
                result.evaluator_name,
                1 if result.passed else 0,
                result.score,
                result.reason,
                json.dumps(case.expected, ensure_ascii=False),
                preview_text(outcome.output_text, limit=2000),
                now_iso(),
            ),
        )
        conn.commit()


def _collect_counts(run_id: str) -> dict[str, int]:
    with get_connection() as conn:
        task_rows = conn.execute(
            "SELECT status, COUNT(*) AS count FROM eval_tasks WHERE run_id = ? GROUP BY status",
            (run_id,),
        ).fetchall()
        result_rows = conn.execute(
            "SELECT passed, COUNT(*) AS count FROM eval_results WHERE run_id = ? GROUP BY passed",
            (run_id,),
        ).fetchall()

    task_counts = {row["status"]: row["count"] for row in task_rows}
    result_counts = {row["passed"]: row["count"] for row in result_rows}
    return {
        "success_count": int(task_counts.get("success", 0)),
        "failed_count": int(task_counts.get("failed", 0)),
        "timeout_count": int(task_counts.get("timeout", 0)),
        "eval_pass_count": int(result_counts.get(1, 0)),
        "eval_fail_count": int(result_counts.get(0, 0)),
    }
