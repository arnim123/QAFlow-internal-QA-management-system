"""seed document templates

Revision ID: 0003_seed_templates
Revises: 0002_domain_schema
Create Date: 2026-11-14

"""

import json
from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

from app.services.template_defaults import default_templates

revision: str = "0003_seed_templates"
down_revision: str | None = "0002_domain_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    present = {
        row[0]
        for row in bind.execute(text("SELECT [type] FROM templates WHERE version = 1"))
    }
    insert = text(
        "INSERT INTO templates ([type], json_schema, columns, version, is_active) "
        "VALUES (:template_type, :json_schema, :columns, 1, 1)"
    )
    for seed in default_templates():
        if seed.template_type.value in present:
            continue
        bind.execute(
            insert,
            {
                "template_type": seed.template_type.value,
                "json_schema": json.dumps(seed.json_schema),
                "columns": json.dumps(seed.columns),
            },
        )


def downgrade() -> None:
    # Version 1 may already be referenced by user stories and requirements.
    # Dropping the table is the previous migration's job.
    pass
