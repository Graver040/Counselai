"""Per-workspace usage metering.

Records one row per billable action (upload, ask, draft, checklist) into the
`usage_logs` table. Metering is best-effort: a failure here must never break the
user's request, so all inserts are wrapped and swallowed with a log line.

Aggregate for billing/quotas with e.g.:
    select workspace_id, action, count(*), sum(input_tokens+output_tokens)
    from usage_logs group by 1, 2;
"""
import logging

from app.core.deps import get_supabase

logger = logging.getLogger(__name__)


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
