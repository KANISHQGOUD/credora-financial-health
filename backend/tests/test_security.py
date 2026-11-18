"""Rate limiting and configuration safety checks."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.core.rate_limit import limiter, reset_all

API = "/api/v1"


@pytest.fixture
def rate_limited() -> None:
    reset_all()
    limiter.enabled = True
    yield
    limiter.enabled = False
    reset_all()


def test_login_guessing_on_one_account_is_limited(client: TestClient, rate_limited: None) -> None:
    body = {"email": "nobody@example.com", "password": "wrong-password"}
    statuses = [client.post(f"{API}/auth/login", json=body).status_code for _ in range(6)]
    assert statuses[:5] == [401] * 5
    assert statuses[5] == 429
    # The limit is per account: another email from the same IP is still allowed.
    other = {"email": "someone-else@example.com", "password": "wrong-password"}
    assert client.post(f"{API}/auth/login", json=other).status_code == 401


def test_a_class_on_one_network_can_sign_up(client: TestClient, rate_limited: None) -> None:
    statuses = [
        client.post(
            f"{API}/auth/register",
            json={"email": f"student{i}@example.com", "password": "a-long-password-123"},
        ).status_code
        for i in range(31)
    ]
    assert statuses[:30] == [201] * 30
    assert statuses[30] == 429


def test_short_jwt_secret_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(jwt_secret_key="too-short")
