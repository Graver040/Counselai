"""Ingestion pipeline. Runs as a FastAPI BackgroundTask for the MVP
(fine on Railway single process). If uploads start timing out at scale,
swap the caller to a queue (e.g. Supabase cron + a worker, or arq/Redis)
without changing this function.

documents.status lifecycle: processing -> ready | failed
"""
import logging

from app.core.config import get_settings
from app.core.deps import get_supabase
from app.services import chunking, embeddings, pdf_processing, vector_store

logger = logging.getLogger(__name__)


def run_ingest(document_id: str, workspace_id: str, storage_path: str) -> None:
    sb = get_supabase()
    s = get_settings()
    try:
        pdf_bytes = sb.storage.from_(s.storage_bucket).download(storage_path)

        pages = pdf_processing.extract_pages(pdf_bytes)
        if pdf_processing.document_is_empty(pages):
            _fail(sb, document_id, "No readable text found (OCR also failed)")
            return

        chunks = chunking.chunk_pages(pages)
        vectors = embeddings.embed_texts([c.content for c in chunks])
        vector_store.upsert_chunks(workspace_id, document_id, chunks, vectors)

        # Persist chunk text in Postgres — source of truth for RAG answers
        rows = [
            {
                "document_id": document_id,
                "workspace_id": workspace_id,
                "chunk_index": c.chunk_index,
                "page_number": c.page_number,
                "content": c.content,
            }
            for c in chunks
        ]
        for i in range(0, len(rows), 500):
            sb.table("document_chunks").insert(rows[i : i + 500]).execute()

        ocr_pages = sum(1 for p in pages if p.used_ocr)
        sb.table("documents").update({
            "status": "ready",
            "page_count": len(pages),
            "chunk_count": len(chunks),
            "ocr_page_count": ocr_pages,
        }).eq("id", document_id).execute()
        logger.info("Ingested %s: %d pages (%d OCR), %d chunks",
                    document_id, len(pages), ocr_pages, len(chunks))

    except Exception as e:
        logger.exception("Ingestion failed for %s", document_id)
        _fail(sb, document_id, str(e)[:500])


def _fail(sb, document_id: str, error: str) -> None:
    sb.table("documents").update(
        {"status": "failed", "error": error}
    ).eq("id", document_id).execute()
