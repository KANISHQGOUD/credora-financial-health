import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LenderAccessGrant(Base):
    __tablename__ = "lender_access_grants"
    __table_args__ = (UniqueConstraint("borrower_id", "lender_id", name="uq_lender_grant_pair"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    borrower_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    lender_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    scope: Mapped[str] = mapped_column(String(40), nullable=False, default="assessment")
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FinancialAssessment(Base):
    __tablename__ = "financial_assessments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    borrower_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    methodology_version: Mapped[str] = mapped_column(String(40), nullable=False)
    reporting_window: Mapped[dict] = mapped_column(JSON, nullable=False)
    overall_category: Mapped[str | None] = mapped_column(String(40))
    summary: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict | None] = mapped_column(JSON)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AssessmentIndicator(Base):
    __tablename__ = "assessment_indicators"
    __table_args__ = (UniqueConstraint("assessment_id", "indicator_name", name="uq_assessment_indicator"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("financial_assessments.id", ondelete="CASCADE"), index=True, nullable=False)
    indicator_name: Mapped[str] = mapped_column(String(80), nullable=False)
    value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    unit: Mapped[str | None] = mapped_column(String(30))
    availability: Mapped[str] = mapped_column(String(30), nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text)


class SyntheticDataRun(Base):
    __tablename__ = "synthetic_data_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    dataset_name: Mapped[str] = mapped_column(String(120), nullable=False)
    seed: Mapped[int | None] = mapped_column()
    generator_version: Mapped[str] = mapped_column(String(40), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
