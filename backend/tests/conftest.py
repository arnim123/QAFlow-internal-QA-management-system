"""Test defaults. The health test does not open a database connection."""

import os

pytest_plugins = ["tests.foundation"]

os.environ.setdefault("ODOO_WRITEBACK_ENABLED", "false")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-qaflow-suite-2026")
os.environ.setdefault("APP_ENV", "local")
os.environ.setdefault(
    "DATABASE_URL",
    "mssql+pyodbc://sa:unused@localhost:1433/qaflow"
    "?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes",
)
