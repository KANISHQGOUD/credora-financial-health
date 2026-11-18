"""Rate limiting for the sign-in and sign-up endpoints.

Two kinds of limit:

* ``limiter`` counts requests per client IP. It is generous (``AUTH_RATE_LIMIT``)
  because a class or office shares one public IP address.
* ``check_login_attempts`` counts sign-in attempts per IP *and* email address
  (``LOGIN_ACCOUNT_RATE_LIMIT``), which stops password guessing against one
  account without blocking everyone else on the same network.

Behind a reverse proxy, run uvicorn with ``--proxy-headers`` so the real client
address is used rather than the proxy's. Counts live in memory, per worker.
"""

from fastapi import HTTPException, Request, status
from limits import parse
from limits.storage import MemoryStorage
from limits.strategies import FixedWindowRateLimiter
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

limiter = Limiter(key_func=get_remote_address, enabled=settings.rate_limit_enabled)

_account_storage = MemoryStorage()
_account_limiter = FixedWindowRateLimiter(_account_storage)
_account_limit = parse(settings.login_account_rate_limit)


def check_login_attempts(request: Request, email: str) -> None:
    """Raise 429 once one IP has tried to sign in to one account too often."""
    if not limiter.enabled:
        return
    if not _account_limiter.hit(_account_limit, "login", get_remote_address(request), email.lower()):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many sign-in attempts for this account. Please wait a minute and try again.",
        )


def reset_all() -> None:
    """Clear every counter (used by tests)."""
    limiter.reset()
    _account_storage.reset()
