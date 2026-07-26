"""Usage router — daily usage snapshot for the current workspace.

Powers the frontend UsageStats (used_today / limit / plan) shown on the
billing page and quota indicators.
"""
from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, get_current_user
from app.services import usage

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("")
def get_usage(user: CurrentUser = Depends(get_current_user)):
    return usage.get_stats(user.workspace_id)
