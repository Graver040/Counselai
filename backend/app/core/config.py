"""Central settings. Reads from .env."""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Existing app config
    DEBUG: bool = Field(default=False)
    DATABASE_URL: str = Field(default="sqlite:///./test.db")
    JWT_SECRET: str = Field(default="supersecretkey")
    JWT_ALGORITHM: str = Field(default="HS256")

    # Supabase
    supabase_url: str = ""
    supabase_service_role_key: str = ""      # server-side only, NEVER ship to frontend
    # NOTE: auth is verified via the project's JWKS endpoint (ES256/RS256) in
    # app.core.deps — NOT via this shared secret. Kept only for legacy HS256
    # projects; unused on current Supabase (asymmetric) JWTs.
    supabase_jwt_secret: str = ""
    storage_bucket: str = "documents"

    # Embeddings (pick ONE provider; dims must match your Pinecone index)
    embedding_provider: str = "openai"       # "openai" | "voyage"
    openai_api_key: str = ""
    voyage_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"   # 1536 dims
    # for Hindi+English, voyage option should be "voyage-multilingual-2" (1024 dims)
    embedding_dims: int = 1536

    # Answering LLM (Claude) — used by /ask, /draft, /checklist
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"  # balanced cost/quality for per-query RAG
    answer_top_k: int = 8                    # chunks retrieved per question

    # Plan limits (billable AI actions per day). The plan itself is read from
    # workspaces.plan; these are the per-plan daily quotas.
    free_daily_limit: int = 10
    starter_daily_limit: int = 200
    enterprise_daily_limit: int = 2000

    # Shared secret for the unauthenticated cron endpoints (/sessions/cleanup).
    # Unset => those endpoints refuse to run (fail closed).
    cron_secret: str = ""

    # Rate limiting. `rate_limit_ai` guards the endpoints that call paid APIs.
    # Storage is in-process (per worker) unless a URI such as redis://… is set.
    rate_limit_default: str = "120/minute"
    rate_limit_ai: str = "10/minute"
    rate_limit_storage_uri: str = ""

    # Pinecone
    pinecone_api_key: str = ""
    pinecone_index: str = "counselai"

    # Ingestion
    chunk_size: int = 800
    chunk_overlap: int = 100
    ocr_min_chars_per_page: int = 25         # below this => page treated as scanned
    max_upload_mb: int = 25

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
