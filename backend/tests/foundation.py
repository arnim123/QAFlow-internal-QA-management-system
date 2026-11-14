"""Module-scoped API and database for foundation tests."""

import os
from collections.abc import Generator
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.database import dispose_engine
from app.core.security import hash_password
from app.main import create_app
from app.models.enums import RoleCode
from app.models.identity import Role, User
from tests.dbutil import alembic, engine, recreate_database, session_factory, test_database_url

PASSWORD = "test-password-1"


@dataclass
class Foundation:
    client: TestClient
    factory: sessionmaker[Session]
    password: str
    emails: dict[RoleCode, str]
    user_ids: dict[RoleCode, int]

    def login(self, role: RoleCode) -> TestClient:
        self.client.cookies.clear()
        response = self.client.post(
            "/api/auth/login",
            json={"email": self.emails[role], "password": self.password},
        )
        assert response.status_code == 200, response.text
        return self.client

    def anonymous(self) -> TestClient:
        self.client.cookies.clear()
        return self.client


@pytest.fixture(scope="module")
def foundation() -> Generator[Foundation]:
    source = test_database_url()
    try:
        recreate_database(source)
    except Exception as exc:
        pytest.skip(f"SQL Server connection failed: {exc}")

    test_url = source.set(database="qaflow_test")
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = test_url.render_as_string(hide_password=False)
    get_settings.cache_clear()
    dispose_engine()
    bind = None
    try:
        alembic("upgrade", "head")
        bind = engine(test_url)
        factory = session_factory(bind)
        emails, user_ids = _seed_users(factory)
        with TestClient(create_app()) as client:
            yield Foundation(client, factory, PASSWORD, emails, user_ids)
    finally:
        if bind is not None:
            bind.dispose()
        dispose_engine()
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
        get_settings.cache_clear()


def _seed_users(factory: sessionmaker[Session]) -> tuple[dict[RoleCode, str], dict[RoleCode, int]]:
    emails = {role: f"{role.value}@qaflow.test" for role in RoleCode}
    user_ids: dict[RoleCode, int] = {}
    with factory() as session:
        roles = {role.code: role for role in session.scalars(select(Role))}
        assert set(roles) == set(RoleCode)
        for code, role in roles.items():
            user = User(
                email=emails[code],
                display_name=code.value,
                role_id=role.id,
                password_hash=None if code == RoleCode.executor_bot else hash_password(PASSWORD),
                is_active=True,
            )
            session.add(user)
            session.flush()
            user_ids[code] = user.id
        session.commit()
    return emails, user_ids
