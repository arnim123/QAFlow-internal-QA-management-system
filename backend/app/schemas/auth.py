"""Sign-in and current-user payloads."""

from pydantic import BaseModel, Field

from app.models.enums import RoleCode


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=72)


class MeOut(BaseModel):
    id: int
    email: str
    display_name: str
    role: RoleCode
