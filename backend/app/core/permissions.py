"""Who can do what. docs/PERMISSIONS.md and tests/test_permissions.py match this table."""

import enum

from app.models.enums import RoleCode


class Permission(enum.StrEnum):
    users_read = "users.read"
    users_manage = "users.manage"
    api_keys_manage = "api_keys.manage"
    settings_read = "settings.read"
    settings_write = "settings.write"
    audit_read = "audit.read"
    jobs_read = "jobs.read"
    jobs_retry = "jobs.retry"
    templates_read = "templates.read"
    templates_manage = "templates.manage"
    priority_override = "priority.override"
    review_flags_read = "review_flags.read"
    review_flags_resolve = "review_flags.resolve"
    cycles_read = "cycles.read"
    cases_read = "cases.read"
    cases_review = "cases.review"
    cases_add = "cases.add"
    cases_final_approve = "cases.final_approve"
    results_validate = "results.validate"
    results_record_manual = "results.record_manual"
    requirements_read = "requirements.read"
    requirements_upload = "requirements.upload"
    reports_read = "reports.read"
    executor_read_approved_set = "executor.read_approved_set"
    executor_submit_results = "executor.submit_results"


_READ = frozenset(
    {
        Permission.cycles_read,
        Permission.cases_read,
        Permission.requirements_read,
        Permission.reports_read,
    }
)

ROLE_PERMISSIONS: dict[RoleCode, frozenset[Permission]] = {
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


def has_permission(role: RoleCode, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS[role]
