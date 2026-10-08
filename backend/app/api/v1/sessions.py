"""Sessions router — device/session limiting to prevent account sharing.

One `active_sessions` row per signed-in device. `session_token` is a fingerprint
(the last 32 chars of the Supabase JWT), never the whole token.

Limits are per WORKSPACE (like usage metering), resolved from `workspaces.plan`:
    free / starter -> 1 device, enterprise -> 5 devices.

A session goes stale after 24h without a heartbeat; the frontend pings
/heartbeat every 5 minutes to keep it alive.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.deps import CurrentUser, get_current_user, get_supabase

router = APIRouter(prefix="/sessions", tags=["sessions"])

# Devices allowed to be signed in at once, per plan.
PLAN_DEVICE_LIMITS = {
    "free": 1,
    "starter": 1,
    "enterprise": 5,
}
DEFAULT_DEVICE_LIMIT = 1

# A session with no heartbeat for this long is treated as gone.
SESSION_TTL = timedelta(hours=24)


def _now() -> datetime:
    # timezone-aware: the columns are timestamptz, and utcnow() is deprecated.
    return datetime.now(timezone.utc)


def _stale_cutoff() -> str:
    return (_now() - SESSION_TTL).isoformat()


def _plan_for_workspace(sb, workspace_id: str) -> str:
    """Resolve the workspace plan, defaulting to 'free' if unset/missing."""
    try:
        res = (
            sb.table("workspaces")
            .select("plan")
            .eq("id", workspace_id)
            .single()
            .execute()
        )
        return (res.data or {}).get("plan") or "free"
    except Exception:
        # Never lock a user out because the plan lookup failed.
        return "free"


class SessionRequest(BaseModel):
    session_token: str   # last 32 chars of the Supabase JWT
    device_info: str     # "Chrome on Mac", "Safari on iPhone", ...


class SessionResponse(BaseModel):
    id: str
    device_info: str | None = None
    last_seen_at: str
    # Returned so the frontend can flag which row is the current device.
    session_token: str


@router.post("/register")
def register_session(
    req: SessionRequest,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
):
    """Claim a device slot. 409 DEVICE_LIMIT_REACHED if the plan is at capacity."""
    sb = get_supabase()

    plan = _plan_for_workspace(sb, user.workspace_id)
    limit = PLAN_DEVICE_LIMITS.get(plan, DEFAULT_DEVICE_LIMIT)

    # Count other live devices on this workspace (excluding this same token, so
    # re-registering an existing device is idempotent rather than self-blocking).
    active = (
        sb.table("active_sessions")
        .select("id, session_token, device_info", count="exact")
        .eq("workspace_id", user.workspace_id)
        .gte("last_seen_at", _stale_cutoff())
        .neq("session_token", req.session_token)
        .execute()
    )
    active_count = active.count or 0

    if active_count >= limit:
        devices = [
            r.get("device_info") for r in (active.data or []) if r.get("device_info")
        ]
        device_str = devices[0] if devices else "another device"
        raise HTTPException(
            status_code=409,
            detail={
                "code": "DEVICE_LIMIT_REACHED",
                "message": f"This account is already active on {device_str}.",
                "active_devices": active_count,
                "limit": limit,
                "plan": plan,
            },
        )

    sb.table("active_sessions").upsert(
        {
            "user_id": user.user_id,
            "workspace_id": user.workspace_id,
            "session_token": req.session_token,
            "device_info": req.device_info,
            "ip_address": request.client.host if request.client else None,
            "last_seen_at": _now().isoformat(),
        },
        on_conflict="session_token",
    ).execute()

    return {"status": "registered", "plan": plan, "limit": limit}


@router.post("/heartbeat")
def heartbeat(
    req: SessionRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Keep this device's slot alive. Called every 5 minutes by the frontend."""
    sb = get_supabase()
    sb.table("active_sessions").update(
        {"last_seen_at": _now().isoformat()}
    ).eq("session_token", req.session_token).eq("user_id", user.user_id).execute()
    return {"status": "ok"}


@router.delete("/logout")
def logout_session(
    req: SessionRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Release this device's slot on explicit sign-out."""
    sb = get_supabase()
    sb.table("active_sessions").delete().eq(
        "session_token", req.session_token
    ).eq("user_id", user.user_id).execute()
    return {"status": "removed"}


@router.get("/list", response_model=list[SessionResponse])
def list_sessions(user: CurrentUser = Depends(get_current_user)):
    """Live sessions for this user — drives the billing page's device list."""
    sb = get_supabase()
    res = (
        sb.table("active_sessions")
        .select("id, device_info, last_seen_at, session_token")
        .eq("user_id", user.user_id)
        .gte("last_seen_at", _stale_cutoff())
        .order("last_seen_at", desc=True)
        .execute()
    )
    return res.data or []


@router.delete("/remove/{session_id}")
def remove_session(
    session_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Sign a specific device out (from the billing page)."""
    sb = get_supabase()
    sb.table("active_sessions").delete().eq("id", session_id).eq(
        "user_id", user.user_id
    ).execute()
    return {"status": "removed"}


@router.delete("/cleanup")
def cleanup_stale_sessions(x_cron_secret: str | None = Header(default=None)):
    """Drop sessions with no heartbeat in 24h. Intended for a daily cron.

    This endpoint has no user auth, so it is gated on a shared secret and fails
    closed: with CRON_SECRET unset it refuses rather than exposing an
    unauthenticated delete.
    """
    secret = get_settings().cron_secret
    if not secret:
        raise HTTPException(503, "Cleanup endpoint not configured (set CRON_SECRET)")
    if x_cron_secret != secret:
        raise HTTPException(401, "Invalid cron secret")

    sb = get_supabase()
    sb.table("active_sessions").delete().lt(
        "last_seen_at", _stale_cutoff()
    ).execute()
    return {"status": "cleaned"}
