"""User administration payloads."""

from pydantic import BaseModel, Field

from app.models.enums import RoleCode


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    display_name: str = Field(min_length=1, max_length=200)
    role: RoleCode
    password: str | None = Field(default=None, max_length=72)


class UserOut(BaseModel):
    id: int
    email: str
    display_name: str
    role: RoleCode
    is_active: bool
