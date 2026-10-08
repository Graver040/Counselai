"""Retrieval — the shared read-side of RAG.

Given a workspace and a natural-language query, embed the query, find the
most similar chunks in that workspace's Pinecone namespace, then pull the
authoritative chunk text back from Postgres (Pinecone only stores a preview).

Returns context objects carrying the page number + filename so callers can
build trustworthy [Page X] citations.
"""
from dataclasses import dataclass

from app.core.config import get_settings
from app.core.deps import get_supabase
from app.services import embeddings, vector_store


@dataclass
class Context:
    document_id: str
    filename: str
    page: int
    chunk_index: int
    content: str
    score: float


def retrieve(workspace_id: str, query: str,
             top_k: int | None = None,
             document_ids: list[str] | None = None) -> list[Context]:
    s = get_settings()
    top_k = top_k or s.answer_top_k

    vector = embeddings.embed_query(query)
    hits = vector_store.query(workspace_id, vector, top_k=top_k,
                              document_ids=document_ids)
    if not hits:
        return []

    sb = get_supabase()
    doc_ids = list({h["document_id"] for h in hits})

    # Authoritative chunk text lives in Postgres, keyed by (document_id, chunk_index).
    rows = (
        sb.table("document_chunks")
        .select("document_id, chunk_index, page_number, content")
        .eq("workspace_id", workspace_id)
        .in_("document_id", doc_ids)
        .execute()
    ).data or []
    by_key = {(r["document_id"], r["chunk_index"]): r for r in rows}

    # Scoped by workspace as well as id: the backend uses the service-role key,
    # which bypasses RLS, so tenant isolation here is ours to enforce. Namespace
    # isolation in the vector store should already guarantee it — this is the
    # defence-in-depth second lock.
    docs = (
        sb.table("documents").select("id, filename")
        .eq("workspace_id", workspace_id)
        .in_("id", doc_ids).execute()
    ).data or []
    filename = {d["id"]: d["filename"] for d in docs}

    out: list[Context] = []
    for h in hits:
        row = by_key.get((h["document_id"], h["chunk_index"]))
        if not row:
            continue  # vector without a matching chunk row (e.g. mid-delete) — skip
        out.append(Context(
            document_id=h["document_id"],
            filename=filename.get(h["document_id"], ""),
            page=row["page_number"],
            chunk_index=h["chunk_index"],
            content=row["content"],
            score=h["score"],
        ))
    return out


def format_context(contexts: list[Context]) -> str:
    """Render retrieved chunks as a numbered, citable source block for the prompt."""
    blocks = []
    for i, c in enumerate(contexts, start=1):
        blocks.append(f"[Source {i} | {c.filename} | Page {c.page}]\n{c.content}")
    return "\n\n".join(blocks)


def citations(contexts: list[Context]) -> list[dict]:
    """De-duplicated (filename, page) list for the API response."""
    seen, out = set(), []
    for c in contexts:
        key = (c.document_id, c.page)
        if key in seen:
            continue
        seen.add(key)
        out.append({"document_id": c.document_id, "filename": c.filename, "page": c.page})
    return out
