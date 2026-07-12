import certifi
import os
os.environ["SSL_CERT_FILE"] = certifi.where()

import jwt as pyjwt
from jwt import PyJWKClient
from fastapi import HTTPException, Request
from supabase import Client, create_client
from functools import lru_cache

from app.core.config import get_settings


@lru_cache
def get_supabase() -> Client:
    s = get_settings()
    return create_client(s.supabase_url, s.supabase_service_role_key)


class CurrentUser:
    def __init__(self, user_id: str, workspace_id: str):
        self.user_id = user_id
        self.workspace_id = workspace_id


_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        s = get_settings()
        _jwks_client = PyJWKClient(
            f"{s.supabase_url}/auth/v1/.well-known/jwks.json",
            cache_keys=True,
        )
    return _jwks_client


def get_current_user(request: Request) -> CurrentUser:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    token = auth.removeprefix("Bearer ").strip()

    try:
        key = _get_jwks_client().get_signing_key_from_jwt(token).key
        payload = pyjwt.decode(
            token, key, algorithms=["ES256", "RS256"], audience="authenticated"
        )
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(401, f"Token error: {type(e).__name__}: {e}")

    user_id = payload["sub"]
    sb = get_supabase()
    member = (
        sb.table("workspace_members")
        .select("workspace_id")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not member.data:
        raise HTTPException(403, "User has no workspace")
    return CurrentUser(user_id=user_id, workspace_id=member.data[0]["workspace_id"])