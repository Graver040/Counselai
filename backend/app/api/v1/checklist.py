"""Checklist router — produce a compliance/response checklist from a notice,
grounded in the workspace's uploaded documents with [Page X] citations.
"""
from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import CurrentUser, get_current_user
from app.services import llm, retrieval, usage

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

    res = llm.checklist(instruction, retrieval.format_context(contexts))
    usage.log(user.workspace_id, user.user_id, "checklist",
              input_tokens=res.input_tokens, output_tokens=res.output_tokens,
              model=res.model, meta={"chunks": len(contexts)})
    return {
        "workspace_id": user.workspace_id,
        "items": llm.parse_checklist(res.text),
        "citations": retrieval.citations(contexts),
    }
