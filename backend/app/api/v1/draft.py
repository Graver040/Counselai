"""Draft router — generate a formal draft response to a notice, grounded in
the workspace's uploaded documents with [Page X] citations.
"""
from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.v1._schemas import InstructionRequest
from app.core.deps import CurrentUser
from app.core.quota import require_quota
from app.core.ratelimit import AI_LIMIT, limiter
from app.services import llm, retrieval, usage

router = APIRouter(prefix="/draft", tags=["draft"])


@router.post("")
@limiter.limit(AI_LIMIT)
def create_draft(request: Request, req: InstructionRequest,
                 user: CurrentUser = Depends(require_quota)):
    instruction = req.instruction
    # what to retrieve against: an explicit query, else the instruction, else a default
    query = req.query or instruction or "notice requirements and response"

    contexts = retrieval.retrieve(
        user.workspace_id, query, document_ids=req.doc_ids()
    )
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
