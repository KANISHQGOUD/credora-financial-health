"""Save, clear and seed sample data."""

import secrets
from datetime import date

from sqlalchemy import delete, exists, select
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.demo.personas import GENERATOR_VERSION, generate
from app.models.audit_log import AuditLog
from app.models.financial import CashReserveRecord, DebtRecord, ExpenseRecord, IncomeRecord, SavingsRecord
from app.models.profile import FinancialProfile
from app.models.records import FinancialAssessment, SyntheticDataRun
from app.models.user import User, UserRole

RECORD_MODELS = {"income": IncomeRecord, "expense": ExpenseRecord, "savings": SavingsRecord, "debt": DebtRecord}
ALL_RECORD_MODELS = [*RECORD_MODELS.values(), CashReserveRecord]


def demo_email(persona_key: str) -> str:
    return f"demo-{persona_key}@example.com"


def has_records(db: Session, user_id) -> bool:
    return any(db.scalar(select(exists().where(model.user_id == user_id))) for model in ALL_RECORD_MODELS)


def load_sample_data(db: Session, user: User, persona_key: str, today: date | None = None) -> SyntheticDataRun:
    """Add a persona's sample records to ``user``'s account (caller commits)."""
    sample = generate(persona_key, today)
    run = SyntheticDataRun(
        user_id=user.id, dataset_name=f"persona:{persona_key}", seed=sample.persona.seed, generator_version=GENERATOR_VERSION,
        parameters={"persona": persona_key, "first_month": sample.first_month.isoformat(), "last_month": sample.last_month.isoformat()},
    )
    db.add(run)
    db.flush()
    for row in sample.rows:
        common = {"user_id": user.id, "period_start": row.period_start, "period_end": row.period_end,
                  "amount": row.amount, "currency": "INR", "synthetic_run_id": run.id}
        if row.kind == "reserve":
            db.add(CashReserveRecord(**common))
            continue
        extra = {"required_payment": row.required_payment} if row.kind == "debt" else {}
        db.add(RECORD_MODELS[row.kind](**common, category=row.category, source_label=row.source_label, **extra))
    db.add(AuditLog(actor_id=user.id, action="sample_data.loaded", resource_type="synthetic_data_run", resource_id=str(run.id)))
    return run


def clear_sample_data(db: Session, user: User) -> int:
    """Remove sample records (via their runs) and assessments based on them (caller commits)."""
    removed = db.execute(delete(SyntheticDataRun).where(SyntheticDataRun.user_id == user.id)).rowcount
    db.execute(delete(FinancialAssessment).where(FinancialAssessment.borrower_id == user.id, FinancialAssessment.is_synthetic.is_(True)))
    if removed:
        db.add(AuditLog(actor_id=user.id, action="sample_data.cleared", resource_type="user", resource_id=str(user.id)))
    return removed


def seed_demo_account(db: Session, persona_key: str, today: date | None = None) -> User:
    """Create or reset one shared demo account with fresh sample data (caller commits)."""
    email = demo_email(persona_key)
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        # Demo accounts are reached through the demo-login endpoint, never with a password.
        user = User(email=email, password_hash=hash_password(secrets.token_urlsafe(32)), role=UserRole.BORROWER, is_demo=True)
        db.add(user)
        db.flush()
        db.add(FinancialProfile(user_id=user.id, display_name=persona_key))
    user.is_demo = True
    for model in ALL_RECORD_MODELS:
        db.execute(delete(model).where(model.user_id == user.id))
    db.execute(delete(SyntheticDataRun).where(SyntheticDataRun.user_id == user.id))
    db.execute(delete(FinancialAssessment).where(FinancialAssessment.borrower_id == user.id))
    load_sample_data(db, user, persona_key, today)
    return user
