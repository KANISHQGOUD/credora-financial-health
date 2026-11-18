"""Rate limiting and configuration safety checks."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.core.rate_limit import limiter

API = "/api/v1"


@pytest.fixture
def rate_limited() -> None:
    limiter.reset()
    limiter.enabled = True
    yield
    limiter.enabled = False
    limiter.reset()


def test_login_is_rate_limited(client: TestClient, rate_limited: None) -> None:
    body = {"email": "nobody@example.com", "password": "wrong-password"}
    statuses = [client.post(f"{API}/auth/login", json=body).status_code for _ in range(11)]
    assert statuses[:10] == [401] * 10
    assert statuses[10] == 429


def test_short_jwt_secret_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(jwt_secret_key="too-short")
