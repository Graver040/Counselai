"""Auth router.

We do NOT issue tokens here. Sign-up and login happen directly against
Supabase Auth from the frontend (supabase-js). The backend only VERIFIES
the resulting JWT via `get_current_user` in `app.core.deps`.

The only endpoint kept here is /me — a convenience for the frontend to
confirm the JWT is valid and to fetch the resolved workspace_id.
"""
from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, get_current_user

router = APIRouter()


@router.get("/me")
def read_users_me(current_user: CurrentUser = Depends(get_current_user)):
    return {
        "user_id": current_user.user_id,
        "workspace_id": current_user.workspace_id,
    }
