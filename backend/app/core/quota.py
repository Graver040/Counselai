"""Daily quota enforcement for billable AI actions.

`usage.get_stats` only *reports* the plan allowance — this dependency is what
enforces it. Routers performing a billable action (ask / draft / checklist)
depend on `require_quota` instead of `get_current_user`.

Fail-open by design: `get_stats` swallows its own errors and reports 0 used, so
a transient Supabase blip degrades to "allowed" rather than locking out paying
users. That trades a little abuse headroom for availability.
"""
from fastapi import Depends, HTTPException

from app.core.deps import CurrentUser, get_current_user
from app.services import usage


def require_quota(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    stats = usage.get_stats(user.workspace_id)
    used, limit = stats["used_today"], stats["limit"]

    if used >= limit:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "DAILY_LIMIT_REACHED",
                "message": (
                    f"You've used all {limit} AI actions for today. "
                    "Your limit resets at midnight UTC."
                ),
                "used_today": used,
                "limit": limit,
                "plan": stats["plan"],
            },
        )
    return user
