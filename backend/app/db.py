import sqlite3
from pathlib import Path

from backend.app.config import sqlite_path_from_url


def get_db_path() -> Path:
    return sqlite_path_from_url()


def get_connection() -> sqlite3.Connection:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_keys (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT,
                api_key_hash TEXT NOT NULL,
                api_key_prefix TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS models (
                id TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                model_name TEXT NOT NULL,
                display_name TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS request_logs (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                api_key_id TEXT,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                status TEXT NOT NULL,
                prompt_preview TEXT,
                output_preview TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                total_tokens INTEGER,
                e2e_latency_ms REAL,
                ttft_ms REAL,
                tokens_per_second REAL,
                error_type TEXT,
                error_message TEXT,
                metadata_json TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS eval_runs (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                case_file TEXT,
                concurrency INTEGER NOT NULL,
                timeout_ms INTEGER NOT NULL,
                retry_count INTEGER NOT NULL,
                status TEXT NOT NULL,
                total_cases INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0,
                timeout_count INTEGER DEFAULT 0,
                eval_pass_count INTEGER DEFAULT 0,
                eval_fail_count INTEGER DEFAULT 0,
                started_at TEXT,
                finished_at TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS eval_tasks (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                case_id TEXT NOT NULL,
                category TEXT,
                prompt TEXT NOT NULL,
                expected_json TEXT,
                status TEXT NOT NULL,
                request_log_id TEXT,
                retry_times INTEGER DEFAULT 0,
                output_text TEXT,
                error_type TEXT,
                error_message TEXT,
                e2e_latency_ms REAL,
                input_tokens INTEGER,
                output_tokens INTEGER,
                total_tokens INTEGER,
                tokens_per_second REAL,
                started_at TEXT,
                finished_at TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS eval_results (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                case_id TEXT NOT NULL,
                evaluator_name TEXT NOT NULL,
                passed INTEGER NOT NULL,
                score REAL,
                reason TEXT,
                expected_json TEXT,
                actual_text TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO models (
                id, provider, model_name, display_name, is_active, created_at
            )
            SELECT
                'model_ollama_qwen2_5_1_5b',
                'ollama',
                'qwen2.5:1.5b',
                'Qwen2.5 1.5B via Ollama',
                1,
                datetime('now')
            WHERE NOT EXISTS (
                SELECT 1 FROM models
                WHERE provider = 'ollama' AND model_name = 'qwen2.5:1.5b'
            )
            """
        )
        conn.commit()
