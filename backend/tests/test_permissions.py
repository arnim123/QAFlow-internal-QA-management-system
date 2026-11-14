"""The permission matrix is the spec. Changing a role's set fails this file."""

import pytest

from app.core.permissions import ROLE_PERMISSIONS, Permission, has_permission
from app.models.enums import RoleCode

_READ = frozenset(
    {
        Permission.cycles_read,
        Permission.cases_read,
        Permission.requirements_read,
        Permission.reports_read,
    }
)

EXPECTED: dict[RoleCode, frozenset[Permission]] = {
    RoleCode.admin: _READ
    | frozenset(
        {
            Permission.users_read,
            Permission.users_manage,
            Permission.api_keys_manage,
            Permission.settings_read,
            Permission.settings_write,
            Permission.audit_read,
            Permission.jobs_read,
            Permission.jobs_retry,
            Permission.templates_read,
            Permission.templates_manage,
            Permission.priority_override,
            Permission.review_flags_read,
            Permission.review_flags_resolve,
        }
    ),
    RoleCode.qa_lead: _READ
    | frozenset(
        {
            Permission.cases_review,
            Permission.priority_override,
            Permission.review_flags_read,
            Permission.review_flags_resolve,
            Permission.audit_read,
            Permission.settings_read,
        }
    ),
    RoleCode.tester: _READ
    | frozenset(
        {
            Permission.cases_review,
            Permission.cases_add,
            Permission.cases_final_approve,
            Permission.results_validate,
            Permission.results_record_manual,
        }
    ),
    RoleCode.requirement_provider: frozenset({Permission.requirements_upload}),
    RoleCode.viewer: _READ,
    RoleCode.executor_bot: frozenset(
        {
            Permission.executor_read_approved_set,
            Permission.executor_submit_results,
        }
    ),
}


@pytest.mark.parametrize("role", list(RoleCode))
def test_permission_matrix(role: RoleCode) -> None:
    assert ROLE_PERMISSIONS[role] == EXPECTED[role]
    for permission in Permission:
        assert has_permission(role, permission) is (permission in EXPECTED[role])


def test_every_role_and_permission_is_listed() -> None:
    assert set(ROLE_PERMISSIONS) == set(RoleCode)
    granted: set[Permission] = set()
    for permissions in ROLE_PERMISSIONS.values():
        granted.update(permissions)
    assert granted == set(Permission)


def test_final_approval_is_tester_only() -> None:
    assert _holders(Permission.cases_final_approve) == {RoleCode.tester}


def test_case_review_is_tester_and_qa_lead() -> None:
    assert _holders(Permission.cases_review) == {RoleCode.tester, RoleCode.qa_lead}


def test_executor_bot_can_only_call_executor_endpoints() -> None:
    permissions = ROLE_PERMISSIONS[RoleCode.executor_bot]
    assert permissions
    assert all(permission.value.startswith("executor.") for permission in permissions)


def test_requirement_provider_can_only_upload_requirement_sources() -> None:
    assert ROLE_PERMISSIONS[RoleCode.requirement_provider] == {Permission.requirements_upload}


def test_viewer_is_read_only() -> None:
    assert ROLE_PERMISSIONS[RoleCode.viewer] == _READ
    assert all(permission.value.endswith(".read") for permission in _READ)


def test_priority_override_is_admin_and_qa_lead() -> None:
    assert _holders(Permission.priority_override) == {RoleCode.admin, RoleCode.qa_lead}


def test_audit_read_is_admin_and_qa_lead() -> None:
    assert _holders(Permission.audit_read) == {RoleCode.admin, RoleCode.qa_lead}


def _holders(permission: Permission) -> set[RoleCode]:
    return {role for role, permissions in ROLE_PERMISSIONS.items() if permission in permissions}
