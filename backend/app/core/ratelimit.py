"""Request rate limiting.

Complements the daily quota rather than duplicating it: the quota caps total
spend per day, this caps burst rate.

Keyed on the caller's bearer-token fingerprint where available. Keying on IP
alone both punishes shared NAT (a whole CA firm behind one address) and is
trivially sidestepped, so IP is only the fallback for unauthenticated calls.

Storage is in-process by default, which means limits apply PER WORKER: two
uvicorn workers allow roughly twice the configured rate. Set
RATE_LIMIT_STORAGE_URI (e.g. redis://…) to share counters across processes.
"""
from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import get_settings


def _client_key(request: Request) -> str:
    """Identify the caller: bearer-token fingerprint, else remote address."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth.removeprefix("Bearer ").strip()
        if token:
            # Same fingerprinting idea as active_sessions: enough to identify a
            # session, not enough to reconstruct the token.
            return f"tok:{token[-32:]}"
    return f"ip:{get_remote_address(request)}"


def _build_limiter() -> Limiter:
    s = get_settings()
    kwargs: dict = {
        "key_func": _client_key,
        "default_limits": [s.rate_limit_default],
    }
    if s.rate_limit_storage_uri:
        kwargs["storage_uri"] = s.rate_limit_storage_uri
    return Limiter(**kwargs)


limiter = _build_limiter()

# Stricter bucket for the endpoints that call paid APIs.
AI_LIMIT = get_settings().rate_limit_ai


def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """429 shaped like the quota error so the frontend handles both alike."""
    return JSONResponse(
        status_code=429,
        content={
            "detail": {
                "code": "RATE_LIMITED",
                "message": (
                    "Too many requests in a short time. "
                    "Please wait a moment and try again."
                ),
                "limit": str(getattr(exc, "detail", "")),
            }
        },
        headers={"Retry-After": "60"},
    )
