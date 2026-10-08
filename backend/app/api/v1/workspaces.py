"""Workspaces router — Supabase-backed.

The previous SQLAlchemy implementation has been removed; workspace
membership lives in the Supabase `workspace_members` table and the
canonical workspace_id for the current user is already resolved by
`get_current_user` in app.core.deps.
"""
from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import CurrentUser, get_current_user, get_supabase

router = APIRouter()


@router.get("/")
def list_workspaces(current_user: CurrentUser = Depends(get_current_user)):
    sb = get_supabase()
    rows = (
        sb.table("workspace_members")
        .select("workspace_id, role, workspaces(id, name, created_at)")
        .eq("user_id", current_user.user_id)
        .execute()
    )
    return [
        {**r["workspaces"], "role": r.get("role")}
        for r in (rows.data or [])
        if r.get("workspaces")
    ]


@router.get("/current")
def current_workspace(current_user: CurrentUser = Depends(get_current_user)):
    sb = get_supabase()
    res = (
        sb.table("workspaces")
        .select("id, name, created_at")
        .eq("id", current_user.workspace_id)
        .limit(1)
        .execute()
    )
    if not res.data:
        raise HTTPException(404, "Workspace not found")
    return res.data[0]
