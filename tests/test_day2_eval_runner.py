from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.db import get_db_path, init_db
from backend.app.eval_runner.case_loader import load_eval_cases
from backend.app.eval_runner import summary
from backend.app.evaluators.router import evaluate_output
from backend.app.main import app
from backend.app.providers.base import ProviderResponse
from backend.app.providers.ollama import OllamaProvider


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'app.db'}")
    monkeypatch.setattr(summary, "RUNS_DIR", tmp_path / "runs")
    init_db()
    return TestClient(app)


def test_load_smoke_cases() -> None:
    cases = load_eval_cases("eval_cases/smoke_cases.jsonl")
    assert len(cases) >= 10
    assert cases[0].id == "format_001"


def test_duplicate_case_id_fails(tmp_path: Path) -> None:
    case_file = tmp_path / "duplicate.jsonl"
    case = {
        "id": "dup",
        "category": "answer",
        "prompt": "answer",
        "expected": {"type": "exact", "text": "A"},
    }
    case_file.write_text(
        json.dumps(case, ensure_ascii=False) + "\n"
        + json.dumps(case, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Duplicate eval case id"):
        load_eval_cases(str(case_file))


def test_rule_evaluators() -> None:
    assert evaluate_output(
        {"type": "json_schema", "required": ["name"]}, '{"name":"Tom"}'
    ).passed
    assert not evaluate_output(
        {"type": "json_schema", "required": ["name"]}, "not-json"
    ).passed
    assert evaluate_output(
        {"type": "keyword", "keywords": ["first token", "latency"]},
        "first token latency",
    ).passed
    assert not evaluate_output(
        {"type": "keyword", "keywords": ["first token", "latency"]},
        "first token",
    ).passed
    assert evaluate_output(
        {
            "type": "tool_call",
            "tool_name": "search_docs",
            "params": {"keyword": "GPU utilization"},
        },
        '{"tool_name":"search_docs","params":{"keyword":"GPU utilization"}}',
    ).passed
    assert not evaluate_output(
        {
            "type": "tool_call",
            "tool_name": "search_docs",
            "params": {"keyword": "GPU utilization"},
        },
        '{"tool_name":"wrong","params":{"keyword":"GPU utilization"}}',
    ).passed
    assert evaluate_output(
        {"type": "safety_refusal", "must_refuse": True}, "抱歉，我不能提供。"
    ).passed
    assert not evaluate_output(
        {"type": "safety_refusal", "must_refuse": True}, "Here is the guide."
    ).passed


def test_eval_run_api_records_tasks_results_and_summary(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_chat(self, model, messages, temperature, max_tokens):
        prompt = messages[0].content
        if "timeout" in prompt:
            await asyncio.sleep(0.02)
            return ProviderResponse(
                content="late",
                raw_response={},
                e2e_latency_ms=20,
                input_tokens=1,
                output_tokens=1,
                total_tokens=2,
                tokens_per_second=1,
                error_type=None,
                error_message=None,
            )
        if "provider_error" in prompt:
            return ProviderResponse(
                content=None,
                raw_response=None,
                e2e_latency_ms=1,
                input_tokens=1,
                output_tokens=0,
                total_tokens=1,
                tokens_per_second=0,
                error_type="provider_error",
                error_message="mock provider error",
            )
        return ProviderResponse(
            content="A",
            raw_response={"message": {"content": "A"}},
            e2e_latency_ms=1,
            input_tokens=1,
            output_tokens=1,
            total_tokens=2,
            tokens_per_second=1000,
            error_type=None,
            error_message=None,
        )

    monkeypatch.setattr(OllamaProvider, "chat", fake_chat)
    user_a = register_login(client, "eval_owner")
    user_b = register_login(client, "eval_other")
    case_file = tmp_path / "eval_cases.jsonl"
    cases = [
        {
            "id": "exact_pass",
            "category": "answer",
            "prompt": "return exact",
            "expected": {"type": "exact", "text": "A"},
        },
        {
            "id": "timeout_case",
            "category": "timeout",
            "prompt": "timeout",
            "expected": {"type": "contains", "text": "timeout"},
        },
        {
            "id": "provider_error_case",
            "category": "provider_error",
            "prompt": "provider_error",
            "expected": {"type": "contains", "text": "provider_error"},
        },
    ]
    case_file.write_text(
        "\n".join(json.dumps(case, ensure_ascii=False) for case in cases) + "\n",
        encoding="utf-8",
    )

    response = client.post(
        "/api/eval/runs",
        headers=bearer(user_a["access_token"]),
        json={
            "name": "pytest-eval",
            "model": "qwen2.5:1.5b",
            "case_file": str(case_file),
            "concurrency": 2,
            "timeout_ms": 1,
            "retry_count": 0,
        },
    )
    assert response.status_code == 200
    body = response.json()
    run_id = body["run_id"]
    assert body["status"] == "finished"

    run_detail = client.get(
        f"/api/eval/runs/{run_id}", headers=bearer(user_a["access_token"])
    )
    assert run_detail.status_code == 200
    run_body = run_detail.json()
    assert run_body["total_cases"] == 3
    assert run_body["success_count"] == 1
    assert run_body["failed_count"] == 1
    assert run_body["timeout_count"] == 1

    tasks = client.get(
        f"/api/eval/runs/{run_id}/tasks", headers=bearer(user_a["access_token"])
    )
    assert tasks.status_code == 200
    task_items = tasks.json()["tasks"]
    assert len(task_items) == 3
    assert {item["status"] for item in task_items} == {"success", "failed", "timeout"}

    results = client.get(
        f"/api/eval/runs/{run_id}/results", headers=bearer(user_a["access_token"])
    )
    assert results.status_code == 200
    result_items = results.json()["results"]
    assert len(result_items) == 3
    assert sum(1 for item in result_items if item["passed"]) == 1

    other_detail = client.get(
        f"/api/eval/runs/{run_id}", headers=bearer(user_b["access_token"])
    )
    assert other_detail.status_code == 404

    summary_path = summary.RUNS_DIR / run_id / "run_summary.json"
    assert summary_path.exists()
    summary_body = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary_body["run_id"] == run_id
    assert summary_body["total_cases"] == 3

    with sqlite3.connect(get_db_path()) as conn:
        task_count = conn.execute(
            "SELECT COUNT(*) FROM eval_tasks WHERE run_id = ?", (run_id,)
        ).fetchone()[0]
        result_count = conn.execute(
            "SELECT COUNT(*) FROM eval_results WHERE run_id = ?", (run_id,)
        ).fetchone()[0]
    assert task_count == 3
    assert result_count == 3


def register_login(client: TestClient, username: str) -> dict[str, str]:
    password = "123456"
    register = client.post(
        "/api/auth/register", json={"username": username, "password": password}
    )
    assert register.status_code == 200
    login = client.post("/api/auth/login", json={"username": username, "password": password})
    assert login.status_code == 200
    return {"access_token": login.json()["access_token"]}


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
