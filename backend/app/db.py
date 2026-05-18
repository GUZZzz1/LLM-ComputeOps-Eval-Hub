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
