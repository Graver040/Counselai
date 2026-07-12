"""Ask router — RAG question answering over the workspace's documents.

Embeds the question, retrieves the most relevant chunks from the workspace's
namespace, and asks Claude to answer strictly from them with [Page X] citations.
"""
from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import CurrentUser, get_current_user
from app.services import llm, retrieval, usage

router = APIRouter(prefix="/ask", tags=["ask"])


@router.post("")
def ask(payload: dict, user: CurrentUser = Depends(get_current_user)):
    question = (payload.get("question") or "").strip()
    if not question:
        raise HTTPException(400, "`question` is required")

    # optional: restrict the search to specific uploaded documents
    document_ids = payload.get("document_ids") or None

    contexts = retrieval.retrieve(user.workspace_id, question, document_ids=document_ids)
    if not contexts:
        return {
            "workspace_id": user.workspace_id,
            "question": question,
            "answer": "I couldn't find anything relevant in your uploaded documents.",
            "citations": [],
        }

    res = llm.answer_question(question, retrieval.format_context(contexts))
    usage.log(user.workspace_id, user.user_id, "ask",
              input_tokens=res.input_tokens, output_tokens=res.output_tokens,
              model=res.model, meta={"chunks": len(contexts)})
    return {
        "workspace_id": user.workspace_id,
        "question": question,
        "answer": res.text,
        "citations": retrieval.citations(contexts),
    }
