"""Process settings. Odoo technical names stay empty until an admin sets them."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ENV_FILES = tuple(
    path
    for path in (Path.cwd() / ".env", _REPO_ROOT / ".env")
    if path.is_file()
)


class Settings(BaseSettings):
    """Runtime configuration. Defaults are operational, not QA-process decisions."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILES or None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "local"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    database_url: str = (
        "mssql+pyodbc://sa:QAFlow_Local_SA_Passw0rd@db:1433/qaflow"
        "?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes"
    )

    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    worker_sleep_seconds: float = 60.0
    job_max_attempts: int = 5
    job_backoff_base_seconds: float = 30
    job_backoff_max_seconds: float = 3600

    jwt_secret: str = ""
    jwt_expire_minutes: int = 480
    admin_email: str = ""
    admin_password: str = ""
    admin_display_name: str = "Administrator"

    odoo_base_url: str = ""
    odoo_database: str = ""
    odoo_username: str = ""
    odoo_api_key: str = ""
    odoo_writeback_enabled: bool = False
    odoo_writeback_dry_run: bool = True
    odoo_qa_cycles_on_first_pass: str = ""

    odoo_field_qa_started: str = ""
    odoo_field_qa_passed: str = ""
    odoo_field_qa_cycles: str = ""
    odoo_field_task_sub_status: str = ""
    odoo_field_estimated_hours: str = ""
    odoo_field_actual_hours: str = ""

    odoo_stage_id_beta_pending: str = ""
    odoo_stage_id_ready_for_live: str = ""
    odoo_stage_id_production_pending: str = ""
    odoo_stage_id_work_in_progress: str = ""
    odoo_stage_id_cancelled: str = ""

    odoo_stage_label_beta_pending: str = "Deployed on Beta and Pending For Testing"
    odoo_stage_label_ready_for_live: str = "Tested on Beta & Ready for Live"
    odoo_stage_label_production_pending: str = "Deployed on Production and Pending for Testing"
    odoo_stage_label_work_in_progress: str = "Work In Progress"
    odoo_stage_label_cancelled: str = "Cancelled/Merged Tasks"

    grokbot_base_url: str = ""
    grokbot_auth_scheme: str = ""

    llm_provider: str = ""
    llm_model: str = ""
    llm_api_key: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
