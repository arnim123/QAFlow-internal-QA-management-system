"""Odoo 19 Project app. Field names and stage ids come from settings.

This module does not call the network. Write-back stays off until
`ODOO_WRITEBACK_ENABLED` is set by an admin.
"""

from dataclasses import dataclass

from app.core.config import get_settings


@dataclass(frozen=True)
class OdooMapping:
    base_url: str
    database: str
    username: str
    writeback_enabled: bool
    dry_run: bool
    qa_cycles_on_first_pass: str
    field_qa_started: str
    field_qa_passed: str
    field_qa_cycles: str
    field_task_sub_status: str
    field_estimated_hours: str
    field_actual_hours: str
    stage_id_beta_pending: str
    stage_id_ready_for_live: str
    stage_id_production_pending: str
    stage_id_work_in_progress: str
    stage_id_cancelled: str
    stage_label_beta_pending: str
    stage_label_ready_for_live: str
    stage_label_production_pending: str
    stage_label_work_in_progress: str
    stage_label_cancelled: str


def mapping() -> OdooMapping:
    settings = get_settings()
    return OdooMapping(
        base_url=settings.odoo_base_url,
        database=settings.odoo_database,
        username=settings.odoo_username,
        writeback_enabled=settings.odoo_writeback_enabled,
        dry_run=settings.odoo_writeback_dry_run,
        qa_cycles_on_first_pass=settings.odoo_qa_cycles_on_first_pass,
        field_qa_started=settings.odoo_field_qa_started,
        field_qa_passed=settings.odoo_field_qa_passed,
        field_qa_cycles=settings.odoo_field_qa_cycles,
        field_task_sub_status=settings.odoo_field_task_sub_status,
        field_estimated_hours=settings.odoo_field_estimated_hours,
        field_actual_hours=settings.odoo_field_actual_hours,
        stage_id_beta_pending=settings.odoo_stage_id_beta_pending,
        stage_id_ready_for_live=settings.odoo_stage_id_ready_for_live,
        stage_id_production_pending=settings.odoo_stage_id_production_pending,
        stage_id_work_in_progress=settings.odoo_stage_id_work_in_progress,
        stage_id_cancelled=settings.odoo_stage_id_cancelled,
        stage_label_beta_pending=settings.odoo_stage_label_beta_pending,
        stage_label_ready_for_live=settings.odoo_stage_label_ready_for_live,
        stage_label_production_pending=settings.odoo_stage_label_production_pending,
        stage_label_work_in_progress=settings.odoo_stage_label_work_in_progress,
        stage_label_cancelled=settings.odoo_stage_label_cancelled,
    )
