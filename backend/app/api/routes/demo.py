"""Sample data for a borrower's own account, and the shared demo logins."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_writable_borrower
from app.auth.security import create_access_token
from app.core.config import settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.demo.personas import PERSONAS
from app.demo.service import clear_sample_data, demo_email, has_records, load_sample_data
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.auth import TokenResponse, UserResponse

router = APIRouter(tags=["sample data"])
PersonaKey = Literal["steady", "freelancer", "stretched"]


class SampleDataRequest(BaseModel):
    persona: PersonaKey


@router.get("/demo/personas")
def list_personas() -> dict:
    """Personas available for sample data, and whether shared demo logins are enabled."""
    return {
        "demo_logins": settings.demo_mode,
        "personas": [{"key": p.key, "label": p.label, "description": p.description} for p in PERSONAS.values()],
    }


@router.post("/demo/sample-data", status_code=status.HTTP_201_CREATED)
def add_sample_data(payload: SampleDataRequest, db: Session = Depends(get_db), user: User = Depends(require_writable_borrower)) -> dict:
    if has_records(db, user.id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Sample data can only be added to an empty account. Delete your records first.")
    run = load_sample_data(db, user, payload.persona)
    db.commit()
    return {"run_id": str(run.id), "persona": payload.persona}


@router.delete("/demo/sample-data", status_code=status.HTTP_204_NO_CONTENT)
def remove_sample_data(db: Session = Depends(get_db), user: User = Depends(require_writable_borrower)) -> None:
    clear_sample_data(db, user)
    db.commit()


@router.post("/auth/demo/{persona}", response_model=TokenResponse)
@limiter.limit(settings.auth_rate_limit)
def demo_login(request: Request, persona: PersonaKey, db: Session = Depends(get_db)) -> TokenResponse:
    """Sign in to a shared, read-only demo account. Only available when DEMO_MODE is on."""
    if not settings.demo_mode:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo accounts are not enabled")
    user = db.scalar(select(User).where(User.email == demo_email(persona), User.is_demo.is_(True)))
    if user is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Demo accounts are not set up yet")
    db.add(AuditLog(actor_id=user.id, action="account.demo_login", resource_type="user", resource_id=str(user.id)))
    db.commit()
    return TokenResponse(access_token=create_access_token(user.id, user.role), user=UserResponse.model_validate(user))
