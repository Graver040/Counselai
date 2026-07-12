"""Pinecone wrapper. One index, one namespace per workspace — this is the
vector-side tenant isolation that mirrors RLS on the Postgres side.

Vector ID format: "{document_id}:{chunk_index}" so deletes by doc are easy.
Chunk text lives in Supabase document_chunks (source of truth); we only put
a short preview + page metadata in Pinecone.
"""
from functools import lru_cache

from pinecone import Pinecone

from app.core.config import get_settings

_UPSERT_BATCH = 100


@lru_cache
def _index():
    s = get_settings()
    return Pinecone(api_key=s.pinecone_api_key).Index(s.pinecone_index)


def upsert_chunks(workspace_id: str, document_id: str,
                  chunks: list, vectors: list[list[float]]) -> None:
    items = [
        {
            "id": f"{document_id}:{c.chunk_index}",
            "values": v,
            "metadata": {
                "document_id": document_id,
                "chunk_index": c.chunk_index,
                "page": c.page_number,
                "preview": c.content[:200],
            },
        }
        for c, v in zip(chunks, vectors)
    ]
    idx = _index()
    for i in range(0, len(items), _UPSERT_BATCH):
        idx.upsert(vectors=items[i : i + _UPSERT_BATCH], namespace=workspace_id)


def query(workspace_id: str, vector: list[float], top_k: int = 8,
          document_ids: list[str] | None = None) -> list[dict]:
    flt = {"document_id": {"$in": document_ids}} if document_ids else None
    res = _index().query(vector=vector, top_k=top_k, namespace=workspace_id,
                         filter=flt, include_metadata=True)
    return [
        {"id": m["id"], "score": m["score"], **m["metadata"]}
        for m in res["matches"]
    ]


def delete_document(workspace_id: str, document_id: str) -> None:
    """Used by the 'delete my documents' feature — required for your DPDP story."""
    _index().delete(filter={"document_id": document_id}, namespace=workspace_id)
