"""String values stored in check constraints. Member values are the database values."""

import enum

from sqlalchemy import Enum


class RoleCode(enum.StrEnum):
    admin = "admin"
    qa_lead = "qa_lead"
    tester = "tester"
    requirement_provider = "requirement_provider"
    viewer = "viewer"
    executor_bot = "executor_bot"


class TemplateType(enum.StrEnum):
    user_story = "user_story"
    requirement = "requirement"
    test_case = "test_case"
    execution_result = "execution_result"
    report = "report"


class SourceKind(enum.StrEnum):
    recording = "recording"
    transcript = "transcript"


class DraftStatus(enum.StrEnum):
    draft = "draft"
    approved = "approved"


class MasterCaseStatus(enum.StrEnum):
    active = "active"
    retired = "retired"


class CaseSource(enum.StrEnum):
    ai = "ai"
    human = "human"


class SetStatus(enum.StrEnum):
    draft = "draft"
    in_review = "in_review"
    approved = "approved"
    sent = "sent"


class ItemOrigin(enum.StrEnum):
    master_regression = "master_regression"
    ai_new = "ai_new"
    manual_new = "manual_new"


class ReviewDecision(enum.StrEnum):
    pending = "pending"
    approved = "approved"
    modified = "modified"
    removed = "removed"


class CycleOutcome(enum.StrEnum):
    PASS = "PASS"
    REWORK = "REWORK"
    RETEST = "RETEST"


class AiResult(enum.StrEnum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    ERROR = "ERROR"


class ValidationDecision(enum.StrEnum):
    confirmed = "confirmed"
    overridden = "overridden"


class ReportType(enum.StrEnum):
    task = "task"
    master = "master"


class JobStatus(enum.StrEnum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


def sa_enum(enum_cls: type[enum.StrEnum], column: str) -> Enum:
    """VARCHAR plus a check constraint. The metadata convention names it ck_<table>_<column>."""

    return Enum(
        enum_cls,
        name=column,
        native_enum=False,
        create_constraint=True,
        length=32,
        values_callable=lambda cls: [member.value for member in cls],
    )
