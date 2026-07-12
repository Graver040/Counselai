"""Draft router — generate a formal draft response to a notice, grounded in
the workspace's uploaded documents with [Page X] citations.
"""
from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import CurrentUser, get_current_user
from app.services import llm, retrieval, usage

router = APIRouter(prefix="/draft", tags=["draft"])


@router.post("")
def create_draft(payload: dict, user: CurrentUser = Depends(get_current_user)):
    instruction = (payload.get("instruction") or "").strip()
    # what to retrieve against: an explicit query, else the instruction, else a default
    query = (payload.get("query") or instruction
             or "notice requirements and response").strip()
    document_ids = payload.get("document_ids") or None

    contexts = retrieval.retrieve(user.workspace_id, query, document_ids=document_ids)
    if not contexts:
        raise HTTPException(404, "No relevant documents found to draft from")

    res = llm.draft_response(instruction, retrieval.format_context(contexts))
    usage.log(user.workspace_id, user.user_id, "draft",
              input_tokens=res.input_tokens, output_tokens=res.output_tokens,
              model=res.model, meta={"chunks": len(contexts)})
    return {
        "workspace_id": user.workspace_id,
        "draft": res.text,
        "citations": retrieval.citations(contexts),
    }
