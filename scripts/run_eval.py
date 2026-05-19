from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.auth import hash_password, new_id, now_iso
from backend.app.db import get_connection, init_db
from backend.app.eval_runner.runner import EvalRunner


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a Day 2 JSONL eval run.")
    parser.add_argument("--username", default="eval_cli")
    parser.add_argument("--model", default="qwen2.5:1.5b")
    parser.add_argument("--case-file", default="eval_cases/smoke_cases.jsonl")
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--timeout-ms", type=int, default=60_000)
    parser.add_argument("--retry-count", type=int, default=0)
    args = parser.parse_args()

    init_db()
    user_id = get_or_create_user(args.username)
    result = asyncio.run(
        EvalRunner().run(
            user_id=user_id,
            name=f"cli-{args.username}",
            model=args.model,
            case_file=args.case_file,
            concurrency=args.concurrency,
            timeout_ms=args.timeout_ms,
            retry_count=args.retry_count,
        )
    )
    summary = result["summary"]
    print(
        json.dumps(
            {
                "run_id": summary["run_id"],
                "total_cases": summary["total_cases"],
                "success_count": summary["success_count"],
                "failed_count": summary["failed_count"],
                "timeout_count": summary["timeout_count"],
                "eval_pass_count": summary["eval_pass_count"],
                "eval_fail_count": summary["eval_fail_count"],
                "pass_rate": summary["eval_pass_rate"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def get_or_create_user(username: str) -> str:
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if row is not None:
            return row["id"]

        user_id = new_id("user")
        conn.execute(
            """
            INSERT INTO users (id, username, password_hash, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, username, hash_password("123456"), now_iso()),
        )
        conn.commit()
        return user_id


if __name__ == "__main__":
    main()
