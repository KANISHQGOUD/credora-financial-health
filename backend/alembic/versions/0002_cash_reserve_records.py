"""Add point-in-time liquid reserve balances.

Revision ID: 0002_cash_reserve_records
Revises: 0001_initial_schema
Create Date: 2026-11-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_cash_reserve_records"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("financial_assessments", sa.Column("details", postgresql.JSONB(astext_type=sa.Text())))
    op.create_table(
        "cash_reserve_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "period_start", "period_end", name="uq_cash_reserve_period"),
        sa.CheckConstraint("amount >= 0", name="ck_cash_reserve_amount_nonnegative"),
        sa.CheckConstraint("period_end >= period_start", name="ck_cash_reserve_period_order"),
    )
    op.create_index("ix_cash_reserve_records_user_id", "cash_reserve_records", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_cash_reserve_records_user_id", table_name="cash_reserve_records")
    op.drop_table("cash_reserve_records")
    op.drop_column("financial_assessments", "details")
