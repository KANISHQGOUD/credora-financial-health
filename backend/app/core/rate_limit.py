"""Per-client rate limiting for the sign-in and sign-up endpoints.

Uses the client IP. Behind a reverse proxy, run uvicorn with ``--proxy-headers``
so the real client address is used rather than the proxy's.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

limiter = Limiter(key_func=get_remote_address, enabled=settings.rate_limit_enabled)
