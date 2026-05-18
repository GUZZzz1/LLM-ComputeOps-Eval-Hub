from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.app.auth import (
    create_access_token,
    generate_api_key,
    get_current_api_key,
    get_current_user,
    get_user_or_api_key,
    hash_api_key,
    hash_password,
    new_id,
    now_iso,
    verify_password,
)
from backend.app.db import get_connection
from backend.app.providers.ollama import OllamaProvider
from backend.app.schemas import (
    ChatCompletionRequest,
    CreateApiKeyRequest,
    CreateApiKeyResponse,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
)
from backend.app.services.request_logger import (
    create_request_log,
    messages_preview,
    preview_text,
)


app = FastAPI(
    title="LLM ComputeOps & Eval Hub",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)
STATIC_DIR = Path(__file__).resolve().parent / "static"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
DOCS_DIR = PROJECT_ROOT / "docs"

if (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


@app.get("/", include_in_schema=False)
def root() -> FileResponse:
    built_index = FRONTEND_DIST / "index.html"
    if built_index.exists():
        return FileResponse(built_index)
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/docs", include_in_schema=False)
def docs_index() -> FileResponse:
    return FileResponse(DOCS_DIR / "index.html")


@app.get("/docs/{doc_path:path}", include_in_schema=False)
def docs_page(doc_path: str) -> FileResponse:
    file_path = (DOCS_DIR / doc_path).resolve()
    docs_root = DOCS_DIR.resolve()

    try:
        file_path.relative_to(docs_root)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Document not found") from exc

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Document not found")

    if file_path.suffix == ".md":
        return FileResponse(file_path, media_type="text/markdown; charset=utf-8")
    return FileResponse(file_path)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/register", response_model=RegisterResponse)
def register(payload: RegisterRequest) -> RegisterResponse:
    user_id = new_id("user")
    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO users (id, username, password_hash, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, payload.username, hash_password(payload.password), now_iso()),
            )
            conn.commit()
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        ) from exc
    return RegisterResponse(user_id=user_id, username=payload.username)


@app.post("/api/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (payload.username,),
        ).fetchone()

    if row is None or not verify_password(payload.password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    return LoginResponse(access_token=create_access_token(row["id"]), user_id=row["id"])


@app.post("/api/api-keys", response_model=CreateApiKeyResponse)
def create_api_key(
    payload: CreateApiKeyRequest,
    current_user: dict = Depends(get_current_user),
) -> CreateApiKeyResponse:
    api_key = generate_api_key()
    api_key_prefix = api_key[:13]
    api_key_id = new_id("key")
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO api_keys (
                id, user_id, name, api_key_hash, api_key_prefix, is_active, created_at
            ) VALUES (?, ?, ?, ?, ?, 1, ?)
            """,
            (
                api_key_id,
                current_user["id"],
                payload.name,
                hash_api_key(api_key),
                api_key_prefix,
                now_iso(),
            ),
        )
        conn.commit()
    return CreateApiKeyResponse(
        api_key=api_key, api_key_prefix=api_key_prefix, name=payload.name
    )


@app.get("/api/models")
def list_models(_: dict = Depends(get_user_or_api_key)) -> dict:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT provider, model_name, display_name, is_active
            FROM models
            WHERE is_active = 1
            ORDER BY created_at ASC
            """
        ).fetchall()
    return {
        "models": [
            {
                "provider": row["provider"],
                "model": row["model_name"],
                "display_name": row["display_name"],
                "active": bool(row["is_active"]),
            }
            for row in rows
        ]
    }


@app.post("/v1/chat/completions")
async def chat_completions(
    payload: ChatCompletionRequest,
    api_auth: dict = Depends(get_current_api_key),
) -> JSONResponse:
    request_id = new_id("req")
    provider_name = "ollama"
    prompt = messages_preview(payload.messages)

    if payload.stream:
        body = _failed_response(
            request_id,
            "validation_error",
            "Day 1 does not support streaming; set stream to false",
        )
        create_request_log(
            request_id=request_id,
            user_id=api_auth["user_id"],
            api_key_id=api_auth["api_key_id"],
            provider=provider_name,
            model=payload.model,
            status="failed",
            prompt_preview=prompt,
            output_preview=None,
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            e2e_latency_ms=0,
            ttft_ms=None,
            tokens_per_second=0,
            error_type="validation_error",
            error_message=body["error"]["message"],
            metadata=payload.metadata,
        )
        return JSONResponse(status_code=400, content=body)

    model_row = _get_active_model(payload.model)
    if model_row is None:
        body = _failed_response(
            request_id,
            "validation_error",
            f"Model is not active or does not exist: {payload.model}",
        )
        create_request_log(
            request_id=request_id,
            user_id=api_auth["user_id"],
            api_key_id=api_auth["api_key_id"],
            provider=provider_name,
            model=payload.model,
            status="failed",
            prompt_preview=prompt,
            output_preview=None,
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            e2e_latency_ms=0,
            ttft_ms=None,
            tokens_per_second=0,
            error_type="validation_error",
            error_message=body["error"]["message"],
            metadata=payload.metadata,
        )
        return JSONResponse(status_code=400, content=body)

    provider = OllamaProvider()
    result = await provider.chat(
        model=payload.model,
        messages=payload.messages,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
    )

    if result.error_type:
        create_request_log(
            request_id=request_id,
            user_id=api_auth["user_id"],
            api_key_id=api_auth["api_key_id"],
            provider=model_row["provider"],
            model=payload.model,
            status="failed",
            prompt_preview=prompt,
            output_preview=None,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            total_tokens=result.total_tokens,
            e2e_latency_ms=result.e2e_latency_ms,
            ttft_ms=None,
            tokens_per_second=result.tokens_per_second,
            error_type=result.error_type,
            error_message=result.error_message,
            metadata=payload.metadata,
        )
        return JSONResponse(
            status_code=504 if result.error_type == "timeout" else 502,
            content=_failed_response(
                request_id, result.error_type, result.error_message or "Provider error"
            ),
        )

    output = result.content or ""
    create_request_log(
        request_id=request_id,
        user_id=api_auth["user_id"],
        api_key_id=api_auth["api_key_id"],
        provider=model_row["provider"],
        model=payload.model,
        status="success",
        prompt_preview=prompt,
        output_preview=preview_text(output),
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        total_tokens=result.total_tokens,
        e2e_latency_ms=result.e2e_latency_ms,
        ttft_ms=None,
        tokens_per_second=result.tokens_per_second,
        error_type=None,
        error_message=None,
        metadata=payload.metadata,
    )
    return JSONResponse(
        content={
            "id": request_id,
            "object": "chat.completion",
            "created": int(time.time()),
            "model": payload.model,
            "provider": model_row["provider"],
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": output},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "total_tokens": result.total_tokens,
            },
            "metrics": {
                "e2e_latency_ms": result.e2e_latency_ms,
                "ttft_ms": None,
                "tokens_per_second": result.tokens_per_second,
            },
            "request_id": request_id,
            "status": "success",
            "error": None,
        }
    )


@app.get("/api/requests")
def list_requests(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
) -> dict:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                id AS request_id, model, provider, status,
                prompt_preview, output_preview,
                input_tokens, output_tokens, total_tokens,
                e2e_latency_ms, ttft_ms, tokens_per_second,
                error_type, created_at
            FROM request_logs
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (current_user["id"], limit),
        ).fetchall()
    return {"requests": [dict(row) for row in rows]}


@app.get("/api/requests/{request_id}")
def get_request_detail(
    request_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                id AS request_id, user_id, api_key_id, provider, model, status,
                prompt_preview, output_preview,
                input_tokens, output_tokens, total_tokens,
                e2e_latency_ms, ttft_ms, tokens_per_second,
                error_type, error_message, metadata_json, created_at
            FROM request_logs
            WHERE id = ? AND user_id = ?
            """,
            (request_id, current_user["id"]),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Request log not found")
    return dict(row)


def _get_active_model(model_name: str) -> sqlite3.Row | None:
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT provider, model_name, display_name
            FROM models
            WHERE model_name = ? AND is_active = 1
            """,
            (model_name,),
        ).fetchone()


def _failed_response(request_id: str, error_type: str, message: str) -> dict:
    return {
        "id": request_id,
        "request_id": request_id,
        "status": "failed",
        "error": {"type": error_type, "message": message},
    }
