"""Link records to sample-data runs and flag shared demo accounts.

Revision ID: 0003_sample_data
Revises: 0002_cash_reserve_records
Create Date: 2026-11-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_sample_data"
down_revision = "0002_cash_reserve_records"
branch_labels = None
depends_on = None

RECORD_TABLES = ["income_records", "expense_records", "savings_records", "debt_records", "cash_reserve_records"]


def upgrade() -> None:
    op.add_column("users", sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()))

    op.add_column("synthetic_data_runs", sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_synthetic_data_runs_user_id", "synthetic_data_runs", "users", ["user_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_synthetic_data_runs_user_id", "synthetic_data_runs", ["user_id"])

    for table in RECORD_TABLES:
        op.add_column(table, sa.Column("synthetic_run_id", postgresql.UUID(as_uuid=True), nullable=True))
        # Deleting a sample-data run deletes the records it generated.
        op.create_foreign_key(f"fk_{table}_synthetic_run_id", table, "synthetic_data_runs", ["synthetic_run_id"], ["id"], ondelete="CASCADE")
        op.create_index(f"ix_{table}_synthetic_run_id", table, ["synthetic_run_id"])


def downgrade() -> None:
    for table in RECORD_TABLES:
        op.drop_index(f"ix_{table}_synthetic_run_id", table_name=table)
        op.drop_constraint(f"fk_{table}_synthetic_run_id", table, type_="foreignkey")
        op.drop_column(table, "synthetic_run_id")
    op.drop_index("ix_synthetic_data_runs_user_id", table_name="synthetic_data_runs")
    op.drop_constraint("fk_synthetic_data_runs_user_id", "synthetic_data_runs", type_="foreignkey")
    op.drop_column("synthetic_data_runs", "user_id")
    op.drop_column("users", "is_demo")
