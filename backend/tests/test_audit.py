"""A settings change writes one audit row, and only admin and qa_lead can read the log."""

import pytest

from app.models.enums import RoleCode
from app.services.errors import BadRequest
from app.services.settings import load_setting_value, store_setting_value, validate_setting_key
from tests.foundation import Foundation


def test_setting_values_round_trip() -> None:
    assert store_setting_value("int", 4) == "4"
    assert load_setting_value("int", "4") == 4
    assert store_setting_value("bool", False) == "false"
    assert load_setting_value("bool", "true") is True
    with pytest.raises(BadRequest):
        store_setting_value("int", True)
    with pytest.raises(BadRequest):
        store_setting_value("str", 1)
    with pytest.raises(BadRequest):
        validate_setting_key("odoo_api_key")
    with pytest.raises(BadRequest):
        validate_setting_key("not_a_known_setting")
    assert validate_setting_key("odoo_field_qa_started").value_type == "str"


def test_settings_update_is_audited_and_hidden_from_the_tester(foundation: Foundation) -> None:
    client = foundation.login(RoleCode.qa_lead)
    current = client.get("/api/settings")
    assert current.status_code == 200
    untouched = next(row for row in current.json() if row["key"] == "odoo_field_qa_passed")
    assert untouched["source"] == "environment"
    assert untouched["value_type"] == "str"
    denied = client.put(
        "/api/settings/odoo_field_qa_started",
        json={"value": "x_qa_started"},
    )
    assert denied.status_code == 403

    admin = foundation.login(RoleCode.admin)
    first = admin.put("/api/settings/odoo_field_qa_started", json={"value": "x_qa_started"})
    assert first.status_code == 200
    assert first.json()["source"] == "database"
    second = admin.put(
        "/api/settings/odoo_field_qa_started",
        json={"value": "x_qa_started_2"},
    )
    assert second.status_code == 200
    assert second.json()["value"] == "x_qa_started_2"
    secret = admin.put("/api/settings/jwt_secret", json={"value": "nope"})
    assert secret.status_code == 400
    wrong_type = admin.put("/api/settings/odoo_field_qa_started", json={"value": 1})
    assert wrong_type.status_code == 400

    lead = foundation.login(RoleCode.qa_lead)
    listed = lead.get(
        "/api/audit-log",
        params={"entity": "setting", "entity_id": "odoo_field_qa_started"},
    )
    assert listed.status_code == 200
    latest = listed.json()[0]
    assert latest["actor"] == foundation.emails[RoleCode.admin]
    assert latest["action"] == "settings.update"
    assert latest["entity"] == "setting"
    assert latest["entity_id"] == "odoo_field_qa_started"
    assert latest["before"] == {"key": "odoo_field_qa_started", "value": "x_qa_started"}
    assert latest["after"] == {"key": "odoo_field_qa_started", "value": "x_qa_started_2"}

    foundation.login(RoleCode.tester)
    assert foundation.client.get("/api/audit-log").status_code == 403
