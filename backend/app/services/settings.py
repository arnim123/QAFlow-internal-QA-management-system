"""Typed settings stored in the database. Secrets stay in the environment."""

from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.catalog import Setting
from app.services.audit import audited
from app.services.errors import BadRequest

SettingSource = Literal["database", "environment"]
StoredValue = str | int | bool
ValueType = Literal["str", "int", "bool"]

_SECRET_MARKERS = ("password", "secret", "api_key", "token", "database_url")

_ALLOWLIST = (
    "odoo_field_qa_started",
    "odoo_field_qa_passed",
    "odoo_field_qa_cycles",
    "odoo_field_task_sub_status",
    "odoo_field_estimated_hours",
    "odoo_field_actual_hours",
    "odoo_stage_id_beta_pending",
    "odoo_stage_id_ready_for_live",
    "odoo_stage_id_production_pending",
    "odoo_stage_id_work_in_progress",
    "odoo_stage_id_cancelled",
    "odoo_stage_label_beta_pending",
    "odoo_stage_label_ready_for_live",
    "odoo_stage_label_production_pending",
    "odoo_stage_label_work_in_progress",
    "odoo_stage_label_cancelled",
)


class SettingType:
    string: ValueType = "str"
    integer: ValueType = "int"
    boolean: ValueType = "bool"


@dataclass(frozen=True)
class SettingSpec:
    key: str
    value_type: ValueType


SPECS: dict[str, SettingSpec] = {
    key: SettingSpec(key=key, value_type=SettingType.string) for key in _ALLOWLIST
}


@dataclass(frozen=True)
class SettingView:
    key: str
    value: StoredValue
    value_type: ValueType
    source: SettingSource


def validate_setting_key(key: str) -> SettingSpec:
    if _is_secret_name(key):
        raise BadRequest("Secrets stay in the environment")
    spec = SPECS.get(key)
    if spec is None:
        raise BadRequest("Unknown setting")
    return spec


def store_setting_value(value_type: ValueType, value: object) -> str:
    if value_type == SettingType.string:
        if not isinstance(value, str):
            raise BadRequest("This setting takes a string")
        return value
    if value_type == SettingType.integer:
        if isinstance(value, bool) or not isinstance(value, int):
            raise BadRequest("This setting takes an integer")
        return str(value)
    if value_type == SettingType.boolean:
        if not isinstance(value, bool):
            raise BadRequest("This setting takes a boolean")
        return "true" if value else "false"
    raise BadRequest("Unsupported setting type")


def load_setting_value(value_type: ValueType, raw: str) -> StoredValue:
    if value_type == SettingType.string:
        return raw
    if value_type == SettingType.integer:
        return int(raw)
    lowered = raw.lower()
    if lowered in {"true", "1"}:
        return True
    if lowered in {"false", "0"}:
        return False
    raise BadRequest("Stored boolean is invalid")


def list_settings(session: Session) -> list[SettingView]:
    stored = {
        row.key: row.value
        for row in session.scalars(select(Setting).where(Setting.key.in_(tuple(SPECS))))
    }
    views: list[SettingView] = []
    for key in sorted(SPECS):
        spec = SPECS[key]
        if key in stored:
            views.append(
                SettingView(
                    key=key,
                    value=load_setting_value(spec.value_type, stored[key]),
                    value_type=spec.value_type,
                    source="database",
                )
            )
        else:
            views.append(
                SettingView(
                    key=key,
                    value=load_setting_value(spec.value_type, _env_value(key)),
                    value_type=spec.value_type,
                    source="environment",
                )
            )
    return views


@audited(action="settings.update", entity="setting")
def set_setting(
    session: Session,
    *,
    actor: str,
    created_by: int | None,
    key: str,
    value: object,
) -> tuple[SettingView, str, dict[str, object] | None, dict[str, object]]:
    spec = validate_setting_key(key)
    stored = store_setting_value(spec.value_type, value)
    row = session.scalar(select(Setting).where(Setting.key == key))
    before = None if row is None else {"key": key, "value": row.value}
    if row is None:
        row = Setting(key=key, value=stored, created_by=created_by)
        session.add(row)
    else:
        row.value = stored
    session.flush()
    view = SettingView(
        key=key,
        value=load_setting_value(spec.value_type, stored),
        value_type=spec.value_type,
        source="database",
    )
    return view, key, before, {"key": key, "value": stored}


def _env_value(key: str) -> str:
    return str(getattr(get_settings(), key))


def _is_secret_name(key: str) -> bool:
    lowered = key.lower()
    return any(marker in lowered for marker in _SECRET_MARKERS)


for _spec in SPECS.values():
    if _is_secret_name(_spec.key):
        raise RuntimeError(f"Refusing to allow a secret setting key: {_spec.key}")
