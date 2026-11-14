"""Login, current user, admin users, and executor API keys."""

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import SESSION_COOKIE, encode_user_token
from app.models.enums import RoleCode
from app.models.identity import ApiKey
from app.services.users import seed_admin
from tests.foundation import PASSWORD, Foundation


def test_login_sets_httponly_cookie_and_me_returns_the_role(foundation: Foundation) -> None:
    foundation.anonymous()
    response = foundation.client.post(
        "/api/auth/login",
        json={"email": foundation.emails[RoleCode.tester], "password": PASSWORD},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "tester"
    cookie = response.headers["set-cookie"].lower()
    assert "qaflow_session=" in cookie
    assert "httponly" in cookie
    assert "samesite=lax" in cookie

    me = foundation.client.get("/api/me")
    assert me.status_code == 200
    assert me.json()["email"] == foundation.emails[RoleCode.tester]
    assert me.json()["role"] == "tester"


def test_wrong_password_is_rejected(foundation: Foundation) -> None:
    foundation.anonymous()
    response = foundation.client.post(
        "/api/auth/login",
        json={"email": foundation.emails[RoleCode.admin], "password": "not-the-password"},
    )
    assert response.status_code == 401
    assert "qaflow_session=" not in response.headers.get("set-cookie", "").lower()


def test_logout_clears_the_session(foundation: Foundation) -> None:
    foundation.login(RoleCode.admin)
    response = foundation.client.post("/api/auth/logout")
    assert response.status_code == 204
    assert foundation.client.get("/api/me").status_code == 401


def test_missing_session_is_unauthorized(foundation: Foundation) -> None:
    assert foundation.anonymous().get("/api/me").status_code == 401


def test_executor_bot_cannot_use_me(foundation: Foundation) -> None:
    foundation.anonymous()
    token = encode_user_token(foundation.user_ids[RoleCode.executor_bot])
    foundation.client.cookies.set(SESSION_COOKIE, token)
    response = foundation.client.get("/api/me")
    assert response.status_code == 403

    foundation.anonymous()
    denied = foundation.client.post(
        "/api/auth/login",
        json={"email": foundation.emails[RoleCode.executor_bot], "password": PASSWORD},
    )
    assert denied.status_code == 401


def test_admin_creates_and_lists_users(foundation: Foundation) -> None:
    client = foundation.login(RoleCode.admin)
    created = client.post(
        "/api/users",
        json={
            "email": "new-tester@qaflow.test",
            "display_name": "New Tester",
            "role": "tester",
            "password": "another-password",
        },
    )
    assert created.status_code == 201
    assert created.json()["role"] == "tester"
    assert "password" not in created.json()

    listed = client.get("/api/users")
    assert listed.status_code == 200
    assert any(row["email"] == "new-tester@qaflow.test" for row in listed.json())

    duplicate = client.post(
        "/api/users",
        json={
            "email": "new-tester@qaflow.test",
            "display_name": "Again",
            "role": "viewer",
            "password": "another-password",
        },
    )
    assert duplicate.status_code == 409

    bot = client.post(
        "/api/users",
        json={
            "email": "second-bot@qaflow.test",
            "display_name": "Second bot",
            "role": "executor_bot",
        },
    )
    assert bot.status_code == 201
    with_password = client.post(
        "/api/users",
        json={
            "email": "third-bot@qaflow.test",
            "display_name": "Third bot",
            "role": "executor_bot",
            "password": "nope-nope-nope",
        },
    )
    assert with_password.status_code == 400

    foundation.login(RoleCode.tester)
    assert foundation.client.get("/api/users").status_code == 403


def test_api_key_is_shown_once_revocable_and_cannot_read_the_audit_log(
    foundation: Foundation,
) -> None:
    client = foundation.login(RoleCode.admin)
    created = client.post(
        "/api/api-keys",
        json={"user_id": foundation.user_ids[RoleCode.executor_bot], "name": "GrokBot"},
    )
    assert created.status_code == 201
    token = created.json()["token"]
    key_id = created.json()["id"]
    assert token.startswith("qf_")

    human = client.post(
        "/api/api-keys",
        json={"user_id": foundation.user_ids[RoleCode.tester], "name": "Not a bot"},
    )
    assert human.status_code == 400

    listed = client.get("/api/api-keys")
    assert listed.status_code == 200
    assert token not in listed.text
    assert "key_hash" not in listed.text
    assert any(row["id"] == key_id and row["last_used_at"] is None for row in listed.json())

    foundation.anonymous()
    me = foundation.client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 403
    audit = foundation.client.get("/api/audit-log", headers={"Authorization": f"Bearer {token}"})
    assert audit.status_code == 403
    with foundation.factory() as session:
        stored = session.scalar(select(ApiKey).where(ApiKey.id == key_id))
        assert stored is not None
        assert stored.last_used_at is not None
        assert stored.key_hash != token

    foundation.login(RoleCode.admin)
    revoked = foundation.client.post(f"/api/api-keys/{key_id}/revoke")
    assert revoked.status_code == 200
    assert revoked.json()["revoked_at"] is not None
    again = foundation.client.post(f"/api/api-keys/{key_id}/revoke")
    assert again.status_code == 409

    foundation.anonymous()
    rejected = foundation.client.get(
        "/api/audit-log",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert rejected.status_code == 401


def test_seed_admin_inserts_once(foundation: Foundation, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_EMAIL", "seeded-admin@qaflow.test")
    monkeypatch.setenv("ADMIN_PASSWORD", "seed-password-1")
    monkeypatch.setenv("ADMIN_DISPLAY_NAME", "Seeded Admin")
    get_settings.cache_clear()
    try:
        with foundation.factory() as session:
            assert seed_admin(session) is True
            assert seed_admin(session) is False
    finally:
        get_settings.cache_clear()

    foundation.anonymous()
    response = foundation.client.post(
        "/api/auth/login",
        json={"email": "seeded-admin@qaflow.test", "password": "seed-password-1"},
    )
    assert response.status_code == 200
    assert response.json()["display_name"] == "Seeded Admin"
    assert response.json()["role"] == "admin"


def test_seed_admin_skips_when_env_is_empty(
    foundation: Foundation,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_EMAIL", "")
    monkeypatch.setenv("ADMIN_PASSWORD", "")
    get_settings.cache_clear()
    try:
        with foundation.factory() as session:
            assert seed_admin(session) is False
    finally:
        get_settings.cache_clear()
