from calendar import monthrange
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


RecordKind = Literal["income", "expense", "savings", "debt", "reserve"]


class FinancialRecordCreate(BaseModel):
    period_start: date
    period_end: date
    amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    currency: Literal["INR"] = "INR"
    category: str | None = Field(default=None, min_length=2, max_length=60)
    source_label: str = Field(default="", max_length=100)
    required_payment: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)

    @field_validator("category", "source_label")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def validate_month(self):
        last_day = date(self.period_start.year, self.period_start.month, monthrange(self.period_start.year, self.period_start.month)[1])
        if self.period_start.day != 1 or self.period_end != last_day:
            raise ValueError("Choose a complete calendar month for the reporting period")
        if self.category is not None and len(self.category) < 2:
            raise ValueError("Enter a category with at least two characters")
        return self


class FinancialRecordResponse(BaseModel):
    id: str
    kind: RecordKind
    period_start: date
    period_end: date
    amount: Decimal
    currency: str
    category: str
    source_label: str | None = None
    required_payment: Decimal | None = None


class AssessmentResponse(BaseModel):
    id: str
    created_at: str
    methodology_version: str
    overall_category: str | None
    summary: str | None
    indicators: list[dict]
    recommendations: list[str]
    recommendation_items: list[dict] = []
    is_synthetic: bool = False
