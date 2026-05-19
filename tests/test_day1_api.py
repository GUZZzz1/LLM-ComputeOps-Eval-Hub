from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.db import get_db_path, init_db
from backend.app.main import app
from backend.app.providers.base import ProviderResponse
from backend.app.providers.ollama import OllamaProvider


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'app.db'}")
    init_db()
    return TestClient(app)


def test_day1_success_flow_and_log_isolation(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_chat(self, model, messages, temperature, max_tokens):
        return ProviderResponse(
            content="TTFT means time to first token.",
            raw_response={"message": {"content": "TTFT means time to first token."}},
            e2e_latency_ms=10.0,
            input_tokens=5,
            output_tokens=15,
            total_tokens=20,
            tokens_per_second=1500.0,
            error_type=None,
            error_message=None,
        )

    monkeypatch.setattr(OllamaProvider, "chat", fake_chat)

    user = register_login_create_key(client, "owner")
    other = register_login_create_key(client, "other")

    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/").status_code == 200

    models_with_token = client.get(
        "/api/models", headers=bearer(user["access_token"])
    )
    assert models_with_token.status_code == 200
    assert models_with_token.json()["models"][0]["model"] == "qwen2.5:1.5b"

    models_with_key = client.get("/api/models", headers=bearer(user["api_key"]))
    assert models_with_key.status_code == 200

    payload = {
        "model": "qwen2.5:1.5b",
        "messages": [{"role": "user", "content": "解释什么是 TTFT"}],
        "temperature": 0.2,
        "max_tokens": 64,
        "stream": False,
        "metadata": {"source": "pytest"},
    }

    access_token_chat = client.post(
        "/v1/chat/completions",
        headers=bearer(user["access_token"]),
        json=payload,
    )
    assert access_token_chat.status_code == 401

    response = client.post(
        "/v1/chat/completions", headers=bearer(user["api_key"]), json=payload
    )
    assert response.status_code == 200
    body = response.json()
    assert set(
        [
            "id",
            "object",
            "created",
            "model",
            "provider",
            "choices",
            "usage",
            "metrics",
            "request_id",
            "status",
            "error",
        ]
    ).issubset(body.keys())
    assert set(["input_tokens", "output_tokens", "total_tokens"]).issubset(
        body["usage"].keys()
    )
    assert set(["e2e_latency_ms", "ttft_ms", "tokens_per_second"]).issubset(
        body["metrics"].keys()
    )

    request_id = body["request_id"]
    owner_logs = client.get("/api/requests", headers=bearer(user["access_token"]))
    assert owner_logs.status_code == 200
    assert any(item["request_id"] == request_id for item in owner_logs.json()["requests"])

    other_logs = client.get("/api/requests", headers=bearer(other["access_token"]))
    assert other_logs.status_code == 200
    assert all(item["request_id"] != request_id for item in other_logs.json()["requests"])

    owner_detail = client.get(
        f"/api/requests/{request_id}", headers=bearer(user["access_token"])
    )
    assert owner_detail.status_code == 200

    other_detail = client.get(
        f"/api/requests/{request_id}", headers=bearer(other["access_token"])
    )
    assert other_detail.status_code == 404

    with sqlite3.connect(get_db_path()) as conn:
        conn.row_factory = sqlite3.Row
        key_row = conn.execute(
            "SELECT api_key_hash, api_key_prefix FROM api_keys WHERE api_key_prefix = ?",
            (user["api_key"][:13],),
        ).fetchone()
        assert key_row is not None
        assert key_row["api_key_hash"] != user["api_key"]
        assert len(key_row["api_key_hash"]) == 64
        assert key_row["api_key_hash"] != hashlib.sha256(
            user["api_key"].encode()
        ).hexdigest()

        log_row = conn.execute(
            "SELECT status, user_id, api_key_id, metadata_json FROM request_logs WHERE id = ?",
            (request_id,),
        ).fetchone()
        assert log_row is not None
        assert log_row["status"] == "success"
        assert log_row["api_key_id"] is not None
        assert '"source": "pytest"' in log_row["metadata_json"]


def test_provider_error_is_logged(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_chat(self, model, messages, temperature, max_tokens):
        return ProviderResponse(
            content=None,
            raw_response=None,
            e2e_latency_ms=3.0,
            input_tokens=2,
            output_tokens=0,
            total_tokens=2,
            tokens_per_second=0,
            error_type="provider_error",
            error_message="Ollama unavailable",
        )

    monkeypatch.setattr(OllamaProvider, "chat", fake_chat)
    user = register_login_create_key(client, "provider_error")

    response = client.post(
        "/v1/chat/completions",
        headers=bearer(user["api_key"]),
        json={
            "model": "qwen2.5:1.5b",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False,
            "metadata": {"source": "failure_test"},
        },
    )
    assert response.status_code == 502
    body = response.json()
    assert body["status"] == "failed"
    assert body["error"]["type"] == "provider_error"

    with sqlite3.connect(get_db_path()) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT status, error_type, api_key_id, metadata_json FROM request_logs WHERE id = ?",
            (body["request_id"],),
        ).fetchone()
        assert row is not None
        assert row["status"] == "failed"
        assert row["error_type"] == "provider_error"
        assert row["api_key_id"] is not None
        assert '"source": "failure_test"' in row["metadata_json"]


def test_auth_and_validation_boundaries(client: TestClient) -> None:
    assert client.get("/api/models").status_code == 401
    assert client.get("/api/models", headers=bearer("bad-token")).status_code == 401
    assert client.post("/api/api-keys", json={"name": "x"}).status_code == 401
    assert (
        client.post(
            "/v1/chat/completions",
            headers=bearer("sk-local-wrong"),
            json={"model": "qwen2.5:1.5b", "messages": []},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/v1/chat/completions",
            headers=bearer("sk-local-wrong"),
            json={"model": "qwen2.5:1.5b"},
        ).status_code
        == 401
    )

    user = register_login_create_key(client, "validation")
    assert (
        client.post(
            "/v1/chat/completions",
            headers=bearer(user["api_key"]),
            json={"model": "qwen2.5:1.5b"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/v1/chat/completions",
            headers=bearer(user["api_key"]),
            json={"model": "qwen2.5:1.5b", "messages": []},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/v1/chat/completions",
            headers=bearer(user["api_key"]),
            json={
                "model": "qwen2.5:1.5b",
                "messages": [{"role": "tool", "content": "hello"}],
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/v1/chat/completions",
            headers=bearer(user["api_key"]),
            json={
                "model": "qwen2.5:1.5b",
                "messages": [{"role": "user", "content": ""}],
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/auth/register",
            json={"username": "short_password", "password": "12345"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/auth/register",
            json={"username": "   ", "password": "123456"},
        ).status_code
        == 422
    )


def test_validation_failures_are_logged(client: TestClient) -> None:
    user = register_login_create_key(client, "validation_logs")

    stream_response = client.post(
        "/v1/chat/completions",
        headers=bearer(user["api_key"]),
        json={
            "model": "qwen2.5:1.5b",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": True,
            "metadata": {"source": "stream_test"},
        },
    )
    assert stream_response.status_code == 400
    stream_body = stream_response.json()
    assert stream_body["error"]["type"] == "validation_error"

    missing_model_response = client.post(
        "/v1/chat/completions",
        headers=bearer(user["api_key"]),
        json={
            "model": "missing-model",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False,
            "metadata": {"source": "missing_model_test"},
        },
    )
    assert missing_model_response.status_code == 400
    missing_model_body = missing_model_response.json()
    assert missing_model_body["error"]["type"] == "validation_error"

    with sqlite3.connect(get_db_path()) as conn:
        conn.row_factory = sqlite3.Row
        stream_row = conn.execute(
            "SELECT status, error_type, metadata_json FROM request_logs WHERE id = ?",
            (stream_body["request_id"],),
        ).fetchone()
        missing_model_row = conn.execute(
            "SELECT status, error_type, metadata_json FROM request_logs WHERE id = ?",
            (missing_model_body["request_id"],),
        ).fetchone()

    assert stream_row is not None
    assert stream_row["status"] == "failed"
    assert stream_row["error_type"] == "validation_error"
    assert '"source": "stream_test"' in stream_row["metadata_json"]

    assert missing_model_row is not None
    assert missing_model_row["status"] == "failed"
    assert missing_model_row["error_type"] == "validation_error"
    assert '"source": "missing_model_test"' in missing_model_row["metadata_json"]


def register_login_create_key(client: TestClient, username: str) -> dict[str, str]:
    password = "123456"
    register = client.post(
        "/api/auth/register", json={"username": username, "password": password}
    )
    assert register.status_code == 200
    login = client.post("/api/auth/login", json={"username": username, "password": password})
    assert login.status_code == 200
    access_token = login.json()["access_token"]
    key = client.post(
        "/api/api-keys",
        headers=bearer(access_token),
        json={"name": f"{username}-key"},
    )
    assert key.status_code == 200
    return {
        "access_token": access_token,
        "api_key": key.json()["api_key"],
    }


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
