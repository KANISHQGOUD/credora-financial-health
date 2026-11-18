from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.intelligence.financial_health import calculate_financial_health
from app.models.audit_log import AuditLog
from app.models.financial import CashReserveRecord, DebtRecord, ExpenseRecord, IncomeRecord, SavingsRecord
from app.models.records import AssessmentIndicator, FinancialAssessment
from app.models.user import User, UserRole
from app.schemas.financial import AssessmentResponse, FinancialRecordCreate, FinancialRecordResponse, RecordKind

router = APIRouter(tags=["financial records"])
BORROWER = require_roles(UserRole.BORROWER)
RECORD_MODELS = {
    "income": IncomeRecord,
    "expense": ExpenseRecord,
    "savings": SavingsRecord,
    "debt": DebtRecord,
}


def _entry(row: Any, kind: str) -> dict[str, Any]:
    return {
        "id": str(row.id), "kind": kind, "period_start": row.period_start, "period_end": row.period_end,
        "amount": row.amount, "currency": row.currency, "category": getattr(row, "category", "Liquid reserves"),
        "source_label": getattr(row, "source_label", None), "required_payment": getattr(row, "required_payment", None),
    }


def _load_records(db: Session, user_id: UUID) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for kind, model in RECORD_MODELS.items():
        rows.extend(_entry(row, kind) for row in db.scalars(select(model).where(model.user_id == user_id)).all())
    return rows


def _load_reserves(db: Session, user_id: UUID) -> list[dict[str, Any]]:
    return [{"period_start": r.period_start, "period_end": r.period_end, "amount": r.amount}
            for r in db.scalars(select(CashReserveRecord).where(CashReserveRecord.user_id == user_id)).all()]


def _assessment_response(row: FinancialAssessment, db: Session) -> dict[str, Any]:
    indicators = db.scalars(select(AssessmentIndicator).where(AssessmentIndicator.assessment_id == row.id).order_by(AssessmentIndicator.indicator_name)).all()
    return {
        "id": str(row.id), "created_at": row.created_at.isoformat(), "methodology_version": row.methodology_version,
        "overall_category": row.overall_category, "summary": row.summary,
        "indicators": [{"name": i.indicator_name, "value": float(i.value) if i.value is not None else None,
                        "unit": i.unit, "status": i.availability, "explanation": i.explanation,
                        "label": (row.details or {}).get("indicator_labels", {}).get(i.indicator_name, i.indicator_name.replace("_", " ").title())}
                       for i in indicators],
        "recommendations": (row.details or {}).get("recommendations", []),
    }


@router.get("/financial-records", response_model=list[FinancialRecordResponse])
def list_financial_records(db: Session = Depends(get_db), user: User = Depends(BORROWER)):
    records = _load_records(db, user.id)
    reserve_rows = db.scalars(select(CashReserveRecord).where(CashReserveRecord.user_id == user.id)).all()
    records.extend(_entry(r, "reserve") for r in reserve_rows)
    records.sort(key=lambda r: (r["period_start"], r["kind"], r["category"]), reverse=True)
    return records[:1000]


@router.post("/financial-records/{kind}", response_model=FinancialRecordResponse, status_code=status.HTTP_201_CREATED)
def create_financial_record(kind: RecordKind, payload: FinancialRecordCreate, db: Session = Depends(get_db), user: User = Depends(BORROWER)):
    if kind == "reserve":
        record = CashReserveRecord(user_id=user.id, period_start=payload.period_start, period_end=payload.period_end,
                                   amount=payload.amount, currency=payload.currency)
    else:
        model = RECORD_MODELS[kind]
        if not payload.category:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Choose a category for this record")
        if kind == "debt" and payload.required_payment is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Enter the required monthly payment for this debt, including 0 if there is no required payment")
        record = model(
            user_id=user.id, period_start=payload.period_start, period_end=payload.period_end,
            amount=payload.amount, currency=payload.currency, category=payload.category,
            source_label=payload.source_label, **({"required_payment": payload.required_payment} if kind == "debt" else {}),
        )
    db.add(record)
    try:
        db.flush()
        db.add(AuditLog(actor_id=user.id, action=f"financial_record.{kind}.created", resource_type=f"financial_record:{kind}", resource_id=str(record.id)))
        db.commit()
        db.refresh(record)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A record of this type and category already exists for that month") from None
    return _entry(record, kind)


@router.delete("/financial-records/{kind}/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_financial_record(kind: RecordKind, record_id: UUID, db: Session = Depends(get_db), user: User = Depends(BORROWER)):
    model = CashReserveRecord if kind == "reserve" else RECORD_MODELS.get(kind)
    record = db.scalar(select(model).where(model.id == record_id, model.user_id == user.id))
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    db.add(AuditLog(actor_id=user.id, action=f"financial_record.{kind}.deleted", resource_type=f"financial_record:{kind}", resource_id=str(record.id)))
    db.delete(record)
    db.commit()


@router.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db), user: User = Depends(BORROWER)):
    records = _load_records(db, user.id)
    reserves = _load_reserves(db, user.id)
    analysis = calculate_financial_health(records, reserves)
    reserves_for_engine = [{**row, "kind": "reserve"} for row in reserves]
    recent_assessment = db.scalar(select(FinancialAssessment).where(FinancialAssessment.borrower_id == user.id).order_by(FinancialAssessment.created_at.desc()).limit(1))
    recent = sorted(records + [_entry(r, "reserve") for r in db.scalars(select(CashReserveRecord).where(CashReserveRecord.user_id == user.id)).all()],
                    key=lambda r: (r["period_start"], r["kind"]), reverse=True)[:10]
    return {
        "analysis": analysis,
        "record_count": len(records) + len(reserves_for_engine),
        "recent_records": recent,
        "latest_assessment": _assessment_response(recent_assessment, db) if recent_assessment else None,
    }


@router.post("/assessments", response_model=AssessmentResponse, status_code=status.HTTP_201_CREATED)
def create_assessment(db: Session = Depends(get_db), user: User = Depends(BORROWER)):
    analysis = calculate_financial_health(_load_records(db, user.id), _load_reserves(db, user.id))
    all_periods = [r["period_start"] for r in _load_records(db, user.id)] + [r["period_start"] for r in _load_reserves(db, user.id)]
    window = {"from": min(all_periods).isoformat(), "through": max(all_periods).isoformat()} if all_periods else {}
    assessment = FinancialAssessment(
        borrower_id=user.id, methodology_version="baseline-heuristic-v1", reporting_window=window,
        overall_category=analysis["overall_category"], summary=analysis["summary"], is_synthetic=False,
        details={"recommendations": analysis["recommendations"],
                 "indicator_labels": {i["name"]: i["label"] for i in analysis["indicators"]}},
    )
    db.add(assessment)
    db.flush()
    for indicator in analysis["indicators"]:
        value = Decimal(str(indicator["value"])) if indicator["value"] is not None else None
        db.add(AssessmentIndicator(
            assessment_id=assessment.id, indicator_name=indicator["name"], value=value,
            unit=indicator["unit"], availability=indicator["status"], explanation=indicator["explanation"],
        ))
    db.add(AuditLog(actor_id=user.id, action="assessment.generated", resource_type="financial_assessment", resource_id=str(assessment.id)))
    db.commit()
    db.refresh(assessment)
    return _assessment_response(assessment, db)


@router.get("/assessments", response_model=list[AssessmentResponse])
def list_assessments(db: Session = Depends(get_db), user: User = Depends(BORROWER)):
    rows = db.scalars(select(FinancialAssessment).where(FinancialAssessment.borrower_id == user.id).order_by(FinancialAssessment.created_at.desc()).limit(50)).all()
    return [_assessment_response(row, db) for row in rows]
