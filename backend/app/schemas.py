from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class RegisterRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=6, max_length=128)

    @field_validator("username")
    @classmethod
    def username_must_not_be_blank(cls, value: str) -> str:
        username = value.strip()
        if not username:
            raise ValueError("Username must not be blank")
        return username


class RegisterResponse(BaseModel):
    user_id: str
    username: str


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str


class CreateApiKeyRequest(BaseModel):
    name: str | None = None


class CreateApiKeyResponse(BaseModel):
    api_key: str
    api_key_prefix: str
    name: str | None


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1)


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage] = Field(min_length=1)
    temperature: float | None = Field(default=0.7, ge=0, le=2)
    max_tokens: int | None = Field(default=256, ge=1, le=8192)
    stream: bool = False
    metadata: dict[str, Any] | None = None


class EvalCase(BaseModel):
    id: str = Field(min_length=1)
    category: str | None = None
    prompt: str = Field(min_length=1)
    expected: dict[str, Any]
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreateEvalRunRequest(BaseModel):
    name: str | None = None
    model: str
    case_file: str = "eval_cases/smoke_cases.jsonl"
    concurrency: int = Field(default=1, ge=1, le=32)
    timeout_ms: int = Field(default=60_000, ge=1)
    retry_count: int = Field(default=0, ge=0, le=10)


class EvalRunResponse(BaseModel):
    run_id: str
    status: str
