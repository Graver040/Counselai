"""Checklist router — produce a compliance/response checklist from a notice,
grounded in the workspace's uploaded documents with [Page X] citations.
"""
from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import CurrentUser, get_current_user
from app.services import llm, retrieval

router = APIRouter(prefix="/checklist", tags=["checklist"])


@router.post("")
def create_checklist(payload: dict, user: CurrentUser = Depends(get_current_user)):
    instruction = (payload.get("instruction") or "").strip()
    query = (payload.get("query") or instruction
             or "compliance requirements, deadlines and documents required").strip()
    document_ids = payload.get("document_ids") or None

    contexts = retrieval.retrieve(user.workspace_id, query, document_ids=document_ids)
    if not contexts:
        raise HTTPException(404, "No relevant documents found to build a checklist from")

    items = llm.build_checklist(instruction, retrieval.format_context(contexts))
    return {
        "workspace_id": user.workspace_id,
        "items": items,
        "citations": retrieval.citations(contexts),
    }
