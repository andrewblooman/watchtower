"""add server defaults for timestamps

Revision ID: 0002_add_defaults
Revises: 0001_init
Create Date: 2026-03-15

"""

from alembic import op
import sqlalchemy as sa

revision = "0002_add_defaults"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("tenants", "created_at", server_default=sa.text("now()"))
    op.alter_column("services", "created_at", server_default=sa.text("now()"))
    op.alter_column("environments", "created_at", server_default=sa.text("now()"))

    op.alter_column("runs", "started_at", server_default=sa.text("now()"))
    op.alter_column("incidents", "detected_at", server_default=sa.text("now()"))
    op.alter_column("events", "ts", server_default=sa.text("now()"))
    op.alter_column("artifacts", "created_at", server_default=sa.text("now()"))


def downgrade() -> None:
    op.alter_column("artifacts", "created_at", server_default=None)
    op.alter_column("events", "ts", server_default=None)
    op.alter_column("incidents", "detected_at", server_default=None)
    op.alter_column("runs", "started_at", server_default=None)

    op.alter_column("environments", "created_at", server_default=None)
    op.alter_column("services", "created_at", server_default=None)
    op.alter_column("tenants", "created_at", server_default=None)

