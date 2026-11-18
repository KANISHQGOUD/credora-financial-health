"""Sample data, demo personas and read-only demo accounts."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.session import SessionLocal
from app.demo.personas import PERSONAS, generate, last_complete_month
from app.demo.service import seed_demo_account
from app.intelligence.financial_health import calculate_financial_health
from factories import payload

API = "/api/v1"


def _analysis_for(persona: str) -> dict:
    sample = generate(persona, date(2026, 11, 18))
    records, reserves = [], []
    for row in sample.rows:
        base = {"period_start": row.period_start, "period_end": row.period_end, "amount": row.amount, "synthetic_run_id": "x"}
        if row.kind == "reserve":
            reserves.append(base)
        else:
            records.append({**base, "kind": row.kind, "category": row.category, "required_payment": row.required_payment})
    return calculate_financial_health(records, reserves)


def _status(analysis: dict, name: str) -> str:
    return next(i["status"] for i in analysis["indicators"] if i["name"] == name)


def test_last_complete_month() -> None:
    assert last_complete_month(date(2026, 11, 18)) == date(2026, 10, 1)
    assert last_complete_month(date(2026, 1, 5)) == date(2025, 12, 1)


def test_generation_is_deterministic_and_covers_six_months() -> None:
    first = generate("freelancer", date(2026, 11, 18))
    second = generate("freelancer", date(2026, 11, 18))
    assert [r.amount for r in first.rows] == [r.amount for r in second.rows]
    assert first.first_month == date(2026, 5, 1)
    assert first.last_month == date(2026, 10, 1)
    assert len({r.period_start for r in first.rows}) == 6


@pytest.mark.parametrize("persona", list(PERSONAS))
def test_persona_has_no_duplicate_rows(persona: str) -> None:
    rows = generate(persona, date(2026, 11, 18)).rows
    keys = [(r.kind, r.period_start, r.category, r.source_label) for r in rows]
    assert len(keys) == len(set(keys))


def test_personas_tell_different_stories() -> None:
    steady, freelancer, stretched = (_analysis_for(p) for p in ("steady", "freelancer", "stretched"))
    assert steady["overall_category"] == "Steady indicators"
    assert _status(steady, "savings_rate") == "favorable"
    assert _status(freelancer, "income_variability") == "attention"
    assert _status(freelancer, "financial_reserve_coverage") == "attention"
    assert _status(stretched, "debt_to_income_ratio") == "attention"
    stretched_ids = {i["id"] for i in stretched["recommendation_items"]}
    assert "trend.latest_month_deficit" in stretched_ids
    assert all(a["is_synthetic"] for a in (steady, freelancer, stretched))


def test_load_and_clear_sample_data(client: TestClient, auth: dict) -> None:
    response = client.post(f"{API}/demo/sample-data", headers=auth, json={"persona": "steady"})
    assert response.status_code == 201, response.text

    dashboard = client.get(f"{API}/dashboard", headers=auth).json()
    assert dashboard["analysis"]["is_synthetic"] is True
    assert dashboard["analysis"]["reporting_months"] == 6
    assert all(r["is_sample"] for r in client.get(f"{API}/financial-records", headers=auth).json())

    saved = client.post(f"{API}/assessments", headers=auth).json()
    assert saved["is_synthetic"] is True

    # Loading twice is refused: the account is no longer empty.
    assert client.post(f"{API}/demo/sample-data", headers=auth, json={"persona": "stretched"}).status_code == 409

    assert client.delete(f"{API}/demo/sample-data", headers=auth).status_code == 204
    assert client.get(f"{API}/financial-records", headers=auth).json() == []
    after = client.get(f"{API}/dashboard", headers=auth).json()
    assert after["analysis"]["is_synthetic"] is False
    assert after["latest_assessment"] is None


def test_clearing_sample_data_keeps_own_records(client: TestClient, auth: dict) -> None:
    client.post(f"{API}/demo/sample-data", headers=auth, json={"persona": "freelancer"})
    own = client.post(f"{API}/financial-records/income", headers=auth, json=payload("2025-01", 1234, category="Gift"))
    assert own.status_code == 201
    client.delete(f"{API}/demo/sample-data", headers=auth)
    remaining = client.get(f"{API}/financial-records", headers=auth).json()
    assert [r["id"] for r in remaining] == [own.json()["id"]]


def test_unknown_persona_is_rejected(client: TestClient, auth: dict) -> None:
    assert client.post(f"{API}/demo/sample-data", headers=auth, json={"persona": "nope"}).status_code == 422


def test_personas_endpoint(client: TestClient) -> None:
    body = client.get(f"{API}/demo/personas").json()
    assert body["demo_logins"] is True
    assert [p["key"] for p in body["personas"]] == ["steady", "freelancer", "stretched"]


def _seed(persona: str) -> None:
    with SessionLocal() as db:
        seed_demo_account(db, persona)
        db.commit()


def test_demo_login_is_read_only(client: TestClient) -> None:
    _seed("stretched")
    login = client.post(f"{API}/auth/demo/stretched")
    assert login.status_code == 200
    assert login.json()["user"]["is_demo"] is True
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    records = client.get(f"{API}/financial-records", headers=headers).json()
    assert records and all(r["is_sample"] for r in records)
    blocked = client.post(f"{API}/financial-records/income", headers=headers, json=payload("2025-01", 1, category="Salary"))
    assert blocked.status_code == 403
    assert "read-only" in blocked.json()["detail"]
    assert client.delete(f"{API}/financial-records/{records[0]['kind']}/{records[0]['id']}", headers=headers).status_code == 403
    assert client.delete(f"{API}/demo/sample-data", headers=headers).status_code == 403
    # Viewing and saving an assessment snapshot are still allowed.
    assert client.post(f"{API}/assessments", headers=headers).status_code == 201


def test_seeding_twice_resets_demo_account(client: TestClient) -> None:
    _seed("steady")
    headers = {"Authorization": f"Bearer {client.post(f'{API}/auth/demo/steady').json()['access_token']}"}
    client.post(f"{API}/assessments", headers=headers)
    first = len(client.get(f"{API}/financial-records", headers=headers).json())
    _seed("steady")
    assert len(client.get(f"{API}/financial-records", headers=headers).json()) == first
    assert client.get(f"{API}/assessments", headers=headers).json() == []


def test_demo_login_needs_seeded_account(client: TestClient) -> None:
    assert client.post(f"{API}/auth/demo/freelancer").status_code == 503


def test_demo_login_disabled_without_demo_mode(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "demo_mode", False)
    assert client.post(f"{API}/auth/demo/steady").status_code == 404
    assert client.get(f"{API}/demo/personas").json()["demo_logins"] is False


def test_demo_accounts_cannot_sign_in_with_a_password(client: TestClient) -> None:
    _seed("steady")
    response = client.post(f"{API}/auth/login", json={"email": "demo-steady@example.com", "password": "anything-at-all"})
    assert response.status_code == 401
