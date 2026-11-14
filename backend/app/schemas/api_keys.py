"""Executor API key payloads. The plaintext token is only on the create response."""

from datetime import datetime

from pydantic import BaseModel, Field


class ApiKeyCreate(BaseModel):
    user_id: int
    name: str = Field(min_length=1, max_length=200)


class ApiKeyCreated(BaseModel):
    id: int
    user_id: int
    name: str
    key_prefix: str
    token: str


class ApiKeyOut(BaseModel):
    id: int
    user_id: int
    name: str
    key_prefix: str
    revoked_at: datetime | None
    last_used_at: datetime | None
