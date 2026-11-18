"""Initial Credora schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-11-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

user_role = sa.Enum("BORROWER", "LENDER", "ADMIN", name="user_role")


def upgrade() -> None:
    op.create_table("users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table("financial_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.String(120)),
        sa.Column("employment_type", sa.String(40)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id"),
    )

    for table, constraint in [
        ("income_records", "uq_income_period_source"),
        ("expense_records", "uq_expense_period_category"),
        ("savings_records", "uq_savings_period_source"),
        ("debt_records", "uq_debt_period_source"),
    ]:
        columns = [
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("period_start", sa.Date(), nullable=False),
            sa.Column("period_end", sa.Date(), nullable=False),
            sa.Column("amount", sa.Numeric(14, 2), nullable=False),
            sa.Column("currency", sa.String(3), nullable=False),
            sa.Column("category", sa.String(60), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        ]
        columns.append(sa.Column("source_label", sa.String(100), nullable=False, server_default=""))
        if table == "debt_records":
            columns.append(sa.Column("required_payment", sa.Numeric(14, 2)))
        constraints = [
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.CheckConstraint("amount >= 0", name=f"ck_{table}_amount_nonnegative"),
            sa.CheckConstraint("period_end >= period_start", name=f"ck_{table}_period_order"),
            sa.CheckConstraint("required_payment IS NULL OR required_payment >= 0", name="ck_debt_payment_nonnegative") if table == "debt_records" else None,
        ]
        constraints = [item for item in constraints if item is not None]
        constraints.append(sa.UniqueConstraint("user_id", "period_start", "period_end", "category", "source_label", name=constraint) if table != "expense_records" else sa.UniqueConstraint("user_id", "period_start", "period_end", "category", name=constraint))
        op.create_table(table, *columns, *constraints)
        op.create_index(f"ix_{table}_user_id", table, ["user_id"])

    op.create_table("lender_access_grants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("borrower_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lender_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope", sa.String(40), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["borrower_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lender_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("borrower_id", "lender_id", name="uq_lender_grant_pair"),
    )
    op.create_index("ix_lender_access_grants_borrower_id", "lender_access_grants", ["borrower_id"])
    op.create_index("ix_lender_access_grants_lender_id", "lender_access_grants", ["lender_id"])

    op.create_table("financial_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("borrower_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("methodology_version", sa.String(40), nullable=False),
        sa.Column("reporting_window", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("overall_category", sa.String(40)),
        sa.Column("summary", sa.Text()),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["borrower_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_financial_assessments_borrower_id", "financial_assessments", ["borrower_id"])

    op.create_table("assessment_indicators",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("indicator_name", sa.String(80), nullable=False),
        sa.Column("value", sa.Numeric(18, 6)),
        sa.Column("unit", sa.String(30)),
        sa.Column("availability", sa.String(30), nullable=False),
        sa.Column("explanation", sa.Text()),
        sa.ForeignKeyConstraint(["assessment_id"], ["financial_assessments.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("assessment_id", "indicator_name", name="uq_assessment_indicator"),
    )
    op.create_index("ix_assessment_indicators_assessment_id", "assessment_indicators", ["assessment_id"])

    op.create_table("synthetic_data_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("dataset_name", sa.String(120), nullable=False),
        sa.Column("seed", sa.Integer()),
        sa.Column("generator_version", sa.String(40), nullable=False),
        sa.Column("parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table("audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True)),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("resource_type", sa.String(80), nullable=False),
        sa.Column("resource_id", sa.String(80)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("synthetic_data_runs")
    op.drop_index("ix_assessment_indicators_assessment_id", table_name="assessment_indicators")
    op.drop_table("assessment_indicators")
    op.drop_index("ix_financial_assessments_borrower_id", table_name="financial_assessments")
    op.drop_table("financial_assessments")
    op.drop_index("ix_lender_access_grants_lender_id", table_name="lender_access_grants")
    op.drop_index("ix_lender_access_grants_borrower_id", table_name="lender_access_grants")
    op.drop_table("lender_access_grants")
    for table in ("debt_records", "savings_records", "expense_records", "income_records"):
        op.drop_index(f"ix_{table}_user_id", table_name=table)
        op.drop_table(table)
    op.drop_table("financial_profiles")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    user_role.drop(op.get_bind(), checkfirst=True)
