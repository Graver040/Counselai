"""Validated request bodies for the billable AI endpoints.

These endpoints call paid APIs (embeddings + Claude), so an unbounded body is a
spend problem, not just a hygiene one: the caps below are a cost control.

`document_ids` is typed as UUID so a malformed or hostile value is rejected at
the edge rather than being forwarded into the vector-store filter.
"""
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

# Generous enough for a long legal question, small enough to bound spend.
MAX_TEXT = 4_000
MAX_QUERY = 1_000
MAX_DOCS = 50


def _clean(v: str | None) -> str | None:
    return v.strip() if isinstance(v, str) else v


class _DocScopedRequest(BaseModel):
    """Optional restriction of retrieval to specific uploaded documents."""

    document_ids: list[UUID] | None = Field(default=None, max_length=MAX_DOCS)

    def doc_ids(self) -> list[str] | None:
        """Vector store and Postgres both want plain strings."""
        return [str(d) for d in self.document_ids] if self.document_ids else None


class AskRequest(_DocScopedRequest):
    question: str = Field(min_length=1, max_length=MAX_TEXT)

    @field_validator("question")
    @classmethod
    def _non_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("`question` is required")
        return v


class InstructionRequest(_DocScopedRequest):
    """Shared by /draft and /checklist.

    `instruction` may be empty — both routers fall back to a default retrieval
    query in that case.
    """

    instruction: str = Field(default="", max_length=MAX_TEXT)
    query: str | None = Field(default=None, max_length=MAX_QUERY)

    @field_validator("instruction", "query")
    @classmethod
    def _strip(cls, v: str | None) -> str | None:
        return _clean(v)
