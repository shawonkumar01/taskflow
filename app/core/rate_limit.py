import math
import time

from fastapi import Request
from limits import RateLimitItem, parse
from limits.storage import storage_from_string
from limits.strategies import MovingWindowRateLimiter

from app.core.config import get_settings
from app.core.exceptions import RateLimitedError

_settings = get_settings()
_strategy = MovingWindowRateLimiter(storage_from_string(_settings.rate_limit_storage_uri))


class RateLimit:
    """FastAPI dependency: N requests per time window, counted per client IP and scope."""

    def __init__(self, limit: str, scope: str) -> None:
        self._item: RateLimitItem = parse(limit)
        self._scope = scope

    def __call__(self, request: Request) -> None:
        if not _settings.rate_limit_enabled:
            return
        client_ip = request.client.host if request.client else "unknown"
        if not _strategy.hit(self._item, self._scope, client_ip):
            stats = _strategy.get_window_stats(self._item, self._scope, client_ip)
            retry_after = max(1, math.ceil(stats.reset_time - time.time()))
            raise RateLimitedError(retry_after=retry_after)


# Applied to every /api/v1 route.
default_rate_limit = RateLimit(_settings.rate_limit_default, "default")
# Strict limits for credential endpoints and for looking up users by email.
auth_rate_limit = RateLimit(_settings.rate_limit_auth, "auth")
member_rate_limit = RateLimit(_settings.rate_limit_auth, "members")
