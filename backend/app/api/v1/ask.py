"""Ask router — RAG question answering over the workspace's documents.

Embeds the question, retrieves the most relevant chunks from the workspace's
namespace, and asks Claude to answer strictly from them with [Page X] citations.

Two variants:
- POST /ask         — buffered JSON response
- POST /ask/stream  — Server-Sent Events (token/citations/done) for live typing
"""
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.core.deps import CurrentUser, get_current_user
from app.services import llm, retrieval, usage

router = APIRouter(prefix="/ask", tags=["ask"])


def _sse(event: str, data: str) -> str:
    # data is JSON-encoded by callers so it is always single-line (SSE-safe).
    return f"event: {event}\ndata: {data}\n\n"


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


@router.post("/stream")
def ask_stream(payload: dict, user: CurrentUser = Depends(get_current_user)):
    question = (payload.get("question") or "").strip()
    if not question:
        raise HTTPException(400, "`question` is required")
    document_ids = payload.get("document_ids") or None

    contexts = retrieval.retrieve(user.workspace_id, question, document_ids=document_ids)

    def event_stream():
        if not contexts:
            yield _sse("token", json.dumps(
                "I couldn't find anything relevant in your uploaded documents."))
            yield _sse("citations", json.dumps([]))
            yield _sse("done", json.dumps({}))
            return

        block = retrieval.format_context(contexts)
        usage_info = {"input_tokens": 0, "output_tokens": 0, "model": None}
        try:
            for ev in llm.stream_answer(question, block):
                if ev["type"] == "token":
                    yield _sse("token", json.dumps(ev["text"]))
                elif ev["type"] == "usage":
                    usage_info = ev
        except Exception as e:  # surface generation errors to the client
            yield _sse("error", json.dumps(str(e)[:200]))
            return

        # pages for the UI, then meter the call, then signal completion
        pages = [c["page"] for c in retrieval.citations(contexts)]
        yield _sse("citations", json.dumps(pages))
        usage.log(user.workspace_id, user.user_id, "ask",
                  input_tokens=usage_info["input_tokens"],
                  output_tokens=usage_info["output_tokens"],
                  model=usage_info["model"], meta={"chunks": len(contexts), "stream": True})
        yield _sse("done", json.dumps({}))

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
