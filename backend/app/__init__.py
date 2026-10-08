from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1 import auth, workspaces, documents, ask, draft, checklist, usage, sessions
from app.core.ratelimit import limiter, rate_limit_handler


def create_app():
    app = FastAPI(title="CounselAI API", version="0.1.0")

    # Rate limiting: a generous default on everything, with a stricter bucket
    # applied per-route to the endpoints that call paid APIs.
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
    app.add_middleware(SlowAPIMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",   # your local frontend
            # "https://app.counselai.in",  # add prod domain when you have it
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(workspaces.router, prefix="/api/v1/workspaces", tags=["workspaces"])
    app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
    app.include_router(ask.router, prefix="/api/v1")
    app.include_router(draft.router, prefix="/api/v1")
    app.include_router(checklist.router, prefix="/api/v1")
    app.include_router(usage.router, prefix="/api/v1")
    app.include_router(sessions.router, prefix="/api/v1")
    return app