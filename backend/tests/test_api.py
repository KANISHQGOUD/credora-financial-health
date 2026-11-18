"""API tests: authentication, ownership, validation and assessments."""

from fastapi.testclient import TestClient

from conftest import PASSWORD, register
from factories import payload

API = "/api/v1"


def test_register_login_and_me(client: TestClient) -> None:
    headers = register(client, "Person@Example.com")
    me = client.get(f"{API}/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "person@example.com"

    login = client.post(f"{API}/auth/login", json={"email": "person@example.com", "password": PASSWORD})
    assert login.status_code == 200
    assert login.json()["access_token"]


def test_wrong_password_is_rejected(client: TestClient) -> None:
    register(client, "someone@example.com")
    response = client.post(f"{API}/auth/login", json={"email": "someone@example.com", "password": "not-the-password"})
    assert response.status_code == 401


def test_duplicate_email_is_rejected(client: TestClient) -> None:
    register(client, "dup@example.com")
    response = client.post(f"{API}/auth/register", json={"email": "dup@example.com", "password": PASSWORD})
    assert response.status_code == 409


def test_public_registration_cannot_choose_a_role(client: TestClient) -> None:
    response = client.post(f"{API}/auth/register", json={"email": "sneaky@example.com", "password": PASSWORD, "role": "lender"})
    assert response.status_code == 201
    assert response.json()["user"]["role"] == "borrower"


def test_short_password_is_rejected(client: TestClient) -> None:
    response = client.post(f"{API}/auth/register", json={"email": "short@example.com", "password": "short"})
    assert response.status_code == 422


def test_records_require_authentication(client: TestClient) -> None:
    assert client.get(f"{API}/financial-records").status_code == 401
    assert client.get(f"{API}/dashboard").status_code == 401


def test_users_only_see_and_delete_their_own_records(client: TestClient) -> None:
    alice, bob = register(client), register(client)
    created = client.post(f"{API}/financial-records/income", headers=alice, json=payload("2026-08", 50000, category="Salary"))
    assert created.status_code == 201
    record_id = created.json()["id"]

    assert client.get(f"{API}/financial-records", headers=bob).json() == []
    assert client.delete(f"{API}/financial-records/income/{record_id}", headers=bob).status_code == 404
    assert len(client.get(f"{API}/financial-records", headers=alice).json()) == 1
    assert client.delete(f"{API}/financial-records/income/{record_id}", headers=alice).status_code == 204
    assert client.get(f"{API}/financial-records", headers=alice).json() == []


def test_duplicate_record_returns_conflict(client: TestClient, auth: dict) -> None:
    body = payload("2026-08", 20000, category="Rent")
    assert client.post(f"{API}/financial-records/expense", headers=auth, json=body).status_code == 201
    assert client.post(f"{API}/financial-records/expense", headers=auth, json=body).status_code == 409


def test_partial_month_is_rejected(client: TestClient, auth: dict) -> None:
    body = {"period_start": "2026-08-02", "period_end": "2026-08-31", "amount": 100, "category": "Salary"}
    assert client.post(f"{API}/financial-records/income", headers=auth, json=body).status_code == 422


def test_debt_requires_payment(client: TestClient, auth: dict) -> None:
    response = client.post(f"{API}/financial-records/debt", headers=auth, json=payload("2026-08", 100000, category="Loan"))
    assert response.status_code == 422
    ok = client.post(f"{API}/financial-records/debt", headers=auth, json=payload("2026-08", 100000, category="Loan", required_payment=0))
    assert ok.status_code == 201


def test_non_reserve_records_require_category(client: TestClient, auth: dict) -> None:
    response = client.post(f"{API}/financial-records/income", headers=auth, json=payload("2026-08", 1000))
    assert response.status_code == 422


def test_reserve_without_category_is_accepted(client: TestClient, auth: dict) -> None:
    response = client.post(f"{API}/financial-records/reserve", headers=auth, json=payload("2026-08", 150000))
    assert response.status_code == 201, response.text
    assert response.json()["category"] == "Liquid reserves"


def test_dashboard_and_saved_assessment(client: TestClient, auth: dict) -> None:
    for when, income, expense in [("2026-08", 50000, 30000), ("2026-09", 52000, 31000)]:
        client.post(f"{API}/financial-records/income", headers=auth, json=payload(when, income, category="Salary"))
        client.post(f"{API}/financial-records/expense", headers=auth, json=payload(when, expense, category="Living"))

    dashboard = client.get(f"{API}/dashboard", headers=auth).json()
    assert dashboard["record_count"] == 4
    assert dashboard["latest_assessment"] is None

    saved = client.post(f"{API}/assessments", headers=auth)
    assert saved.status_code == 201
    body = saved.json()
    assert body["methodology_version"].startswith("baseline-heuristic")
    names = {i["name"] for i in body["indicators"]}
    assert {"average_monthly_income", "expense_to_income_ratio", "savings_rate"} <= names
    assert body["recommendations"]

    history = client.get(f"{API}/assessments", headers=auth).json()
    assert [a["id"] for a in history] == [body["id"]]
    assert client.get(f"{API}/dashboard", headers=auth).json()["latest_assessment"]["id"] == body["id"]
