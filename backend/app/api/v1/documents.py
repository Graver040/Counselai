"""Documents API — upload kicks off background ingestion.

POST   /api/v1/documents          multipart PDF upload
GET    /api/v1/documents          list workspace documents
GET    /api/v1/documents/{id}     status (frontend polls this)
DELETE /api/v1/documents/{id}     full wipe: storage + chunks + vectors
"""
import uuid

from fastapi import (APIRouter, BackgroundTasks, Depends, File,
                     HTTPException, UploadFile)

from app.core.config import get_settings
from app.core.deps import CurrentUser, get_current_user, get_supabase
from app.services import usage, vector_store
from app.workers.ingest import run_ingest

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", status_code=202)
async def upload_document(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
):
    s = get_settings()
    if file.content_type not in ("application/pdf", "application/x-pdf"):
        raise HTTPException(415, "Only PDF files are supported")

    pdf_bytes = await file.read()
    if len(pdf_bytes) > s.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {s.max_upload_mb} MB limit")
    if not pdf_bytes.startswith(b"%PDF"):
        raise HTTPException(415, "File is not a valid PDF")

    doc_id = str(uuid.uuid4())
    storage_path = f"{user.workspace_id}/{doc_id}.pdf"

    sb = get_supabase()
    sb.storage.from_(s.storage_bucket).upload(
        storage_path, pdf_bytes, {"content-type": "application/pdf"}
    )
    try:
        sb.table("documents").insert({
            "id": doc_id,
            "workspace_id": user.workspace_id,
            "uploaded_by": user.user_id,
            "filename": file.filename,
            "storage_path": storage_path,
            "mime_type": "application/pdf",
            "file_size": len(pdf_bytes),
            "status": "processing",
        }).execute()
    except Exception:
        # roll back the orphaned storage object if the DB row can't be created
        sb.storage.from_(s.storage_bucket).remove([storage_path])
        raise HTTPException(500, "Failed to create document record")

    usage.log(user.workspace_id, user.user_id, "upload",
              document_id=doc_id, meta={"bytes": len(pdf_bytes)})
    background.add_task(run_ingest, doc_id, user.workspace_id, storage_path)
    return {"id": doc_id, "status": "processing"}


@router.get("")
def list_documents(user: CurrentUser = Depends(get_current_user)):
    sb = get_supabase()
    res = (
        sb.table("documents")
        .select("id, filename, status, page_count, created_at")
        .eq("workspace_id", user.workspace_id)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data


@router.get("/{doc_id}")
def get_document(doc_id: str, user: CurrentUser = Depends(get_current_user)):
    sb = get_supabase()
    res = (
        sb.table("documents").select("*")
        .eq("id", doc_id).eq("workspace_id", user.workspace_id)
        .execute()
    )
    if not res.data:
        raise HTTPException(404, "Document not found")
    return res.data[0]


@router.delete("/{doc_id}", status_code=204)
def delete_document(doc_id: str, user: CurrentUser = Depends(get_current_user)):
    """Full deletion — storage, chunks, vectors. Your DPDP/confidentiality feature."""
    sb = get_supabase()
    s = get_settings()
    res = (
        sb.table("documents").select("storage_path")
        .eq("id", doc_id).eq("workspace_id", user.workspace_id)
        .execute()
    )
    if not res.data:
        raise HTTPException(404, "Document not found")

    vector_store.delete_document(user.workspace_id, doc_id)
    sb.table("document_chunks").delete().eq("document_id", doc_id).execute()
    sb.storage.from_(s.storage_bucket).remove([res.data[0]["storage_path"]])
    sb.table("documents").delete().eq("id", doc_id).execute()
