from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1)


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
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    temperature: float | None = 0.7
    max_tokens: int | None = 256
    stream: bool = False
    metadata: dict[str, Any] | None = None
