"""Checklist router — produce a compliance/response checklist from a notice,
grounded in the workspace's uploaded documents with [Page X] citations.
"""
from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.v1._schemas import InstructionRequest
from app.core.deps import CurrentUser
from app.core.quota import require_quota
from app.core.ratelimit import AI_LIMIT, limiter
from app.services import llm, retrieval, usage

router = APIRouter(prefix="/checklist", tags=["checklist"])


@router.post("")
@limiter.limit(AI_LIMIT)
def create_checklist(request: Request, req: InstructionRequest,
                     user: CurrentUser = Depends(require_quota)):
    instruction = req.instruction
    query = (req.query or instruction
             or "compliance requirements, deadlines and documents required")

    contexts = retrieval.retrieve(
        user.workspace_id, query, document_ids=req.doc_ids()
    )
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
