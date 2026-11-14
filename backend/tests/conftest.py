"""Test defaults. The health test does not open a database connection."""

import os

os.environ.setdefault("ODOO_WRITEBACK_ENABLED", "false")
os.environ.setdefault(
    "DATABASE_URL",
    "mssql+pyodbc://sa:unused@localhost:1433/qaflow"
    "?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes",
)
