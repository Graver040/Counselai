"""Per-workspace usage metering.

Records one row per billable action (upload, ask, draft, checklist) into the
`usage_logs` table. Metering is best-effort: a failure here must never break the
user's request, so all inserts are wrapped and swallowed with a log line.

Aggregate for billing/quotas with e.g.:
    select workspace_id, action, count(*), sum(input_tokens+output_tokens)
    from usage_logs group by 1, 2;
"""
import logging
from datetime import datetime, timezone

from app.core.config import get_settings
from app.core.deps import get_supabase

logger = logging.getLogger(__name__)

# Actions that count against a plan's daily quota (uploads are free).
_BILLABLE = ["ask", "draft", "checklist"]


def get_stats(workspace_id: str) -> dict:
    """Usage snapshot for the current workspace (drives the frontend UsageStats)."""
    s = get_settings()
    start_of_day = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ).isoformat()

    used_today = 0
    try:
        res = (
            get_supabase().table("usage_logs")
            .select("id", count="exact")
            .eq("workspace_id", workspace_id)
            .in_("action", _BILLABLE)
            .gte("created_at", start_of_day)
            .execute()
        )
        used_today = res.count or 0
    except Exception:
        logger.warning("get_stats failed for ws=%s", workspace_id, exc_info=True)

    # TODO(billing): resolve real plan from a subscription/profile row.
    plan = "free"
    limit = s.free_daily_limit if plan == "free" else s.starter_daily_limit
    return {
        "used_today": used_today,
        "limit": limit,
        "plan": plan,
        "plan_expires_at": None,
    }


def log(workspace_id: str, user_id: str, action: str, *,
        document_id: str | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        model: str | None = None,
        meta: dict | None = None) -> None:
    try:
        get_supabase().table("usage_logs").insert({
            "workspace_id": workspace_id,
            "user_id": user_id,
            "action": action,
            "document_id": document_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "model": model,
            "meta": meta or {},
        }).execute()
    except Exception:
        # never fail the request because metering failed
        logger.warning("usage log failed for action=%s ws=%s", action, workspace_id,
                       exc_info=True)
