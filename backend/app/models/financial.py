import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PeriodRecord(Base):
    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    category: Mapped[str] = mapped_column(String(60), nullable=False)
    source_label: Mapped[str] = mapped_column(String(100), nullable=False, default="", server_default="")
    synthetic_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("synthetic_data_runs.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class IncomeRecord(PeriodRecord):
    __tablename__ = "income_records"
    __table_args__ = (
        UniqueConstraint("user_id", "period_start", "period_end", "category", "source_label", name="uq_income_period_source"),
        CheckConstraint("amount >= 0", name="ck_income_amount_nonnegative"),
        CheckConstraint("period_end >= period_start", name="ck_income_period_order"),
    )


class ExpenseRecord(PeriodRecord):
    __tablename__ = "expense_records"
    __table_args__ = (
        UniqueConstraint("user_id", "period_start", "period_end", "category", name="uq_expense_period_category"),
        CheckConstraint("amount >= 0", name="ck_expense_amount_nonnegative"),
        CheckConstraint("period_end >= period_start", name="ck_expense_period_order"),
    )


class SavingsRecord(PeriodRecord):
    __tablename__ = "savings_records"
    __table_args__ = (
        UniqueConstraint("user_id", "period_start", "period_end", "category", "source_label", name="uq_savings_period_source"),
        CheckConstraint("amount >= 0", name="ck_savings_amount_nonnegative"),
        CheckConstraint("period_end >= period_start", name="ck_savings_period_order"),
    )


class DebtRecord(PeriodRecord):
    __tablename__ = "debt_records"
    __table_args__ = (
        UniqueConstraint("user_id", "period_start", "period_end", "category", "source_label", name="uq_debt_period_source"),
        CheckConstraint("amount >= 0", name="ck_debt_balance_nonnegative"),
        CheckConstraint("required_payment IS NULL OR required_payment >= 0", name="ck_debt_payment_nonnegative"),
        CheckConstraint("period_end >= period_start", name="ck_debt_period_order"),
    )

    required_payment: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))


class CashReserveRecord(Base):
    """A point-in-time liquid reserve balance reported for a period."""

    __tablename__ = "cash_reserve_records"
    __table_args__ = (
        UniqueConstraint("user_id", "period_start", "period_end", name="uq_cash_reserve_period"),
        CheckConstraint("amount >= 0", name="ck_cash_reserve_amount_nonnegative"),
        CheckConstraint("period_end >= period_start", name="ck_cash_reserve_period_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    synthetic_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("synthetic_data_runs.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
