"""Admin settings payloads. Values are typed by the settings service."""

from typing import Literal

from pydantic import BaseModel


class SettingOut(BaseModel):
    key: str
    value: str | int | bool
    value_type: Literal["str", "int", "bool"]
    source: Literal["database", "environment"]


class SettingUpdate(BaseModel):
    value: str | int | bool
