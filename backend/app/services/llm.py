"""Claude wrapper for the answering endpoints.

Grounded generation only: every prompt is fed the retrieved source block and
told to answer strictly from it and cite [Page X]. The system prompt is marked
for prompt caching since it is identical across every request.
"""
import json

from app.core.config import get_settings

_SYSTEM = (
    "You are CounselAI, an assistant for Indian Chartered Accountants and lawyers. "
    "You answer questions about tax notices, GST, and legal documents that the user "
    "has uploaded. Rules:\n"
    "1. Answer ONLY from the provided sources. If the sources do not contain the "
    "answer, say so plainly — never invent facts, sections, dates, or amounts.\n"
    "2. Cite every claim inline as [Page X] using the page numbers shown on each source.\n"
    "3. Be precise and professional. Use Indian tax/legal terminology correctly.\n"
    "4. Do not give definitive legal advice; frame guidance as informational."
)


def _client():
    from anthropic import Anthropic
    return Anthropic(api_key=get_settings().anthropic_api_key)


def _complete(user_prompt: str, max_tokens: int = 1500) -> str:
    s = get_settings()
    resp = _client().messages.create(
        model=s.claude_model,
        max_tokens=max_tokens,
        system=[{"type": "text", "text": _SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_prompt}],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()


def answer_question(question: str, source_block: str) -> str:
    return _complete(
        f"Sources:\n\n{source_block}\n\n"
        f"Question: {question}\n\n"
        "Answer the question using only the sources above, with [Page X] citations."
    )


def draft_response(instruction: str, source_block: str) -> str:
    return _complete(
        f"Sources (the notice and related documents):\n\n{source_block}\n\n"
        f"Task: Draft a formal, professional response to the above on behalf of the "
        f"assessee. {instruction}\n\n"
        "Ground every factual reference in the sources and cite [Page X]. Produce a "
        "ready-to-edit draft (salutation, body, closing).",
        max_tokens=2500,
    )


def build_checklist(instruction: str, source_block: str) -> list[str]:
    raw = _complete(
        f"Sources (the notice and related documents):\n\n{source_block}\n\n"
        f"Task: Produce a compliance/response checklist of concrete action items the "
        f"assessee must complete to respond correctly. {instruction}\n\n"
        "Return ONLY a JSON array of strings, each an action item ending with its "
        "[Page X] citation. No prose outside the JSON.",
        max_tokens=1500,
    )
    return _parse_json_list(raw)


def _parse_json_list(raw: str) -> list[str]:
    """Claude usually returns clean JSON; strip fences / slice to the array if not."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("\n") + 1:] if "\n" in text else text
    start, end = text.find("["), text.rfind("]")
    if start != -1 and end != -1:
        try:
            items = json.loads(text[start:end + 1])
            return [str(x) for x in items]
        except json.JSONDecodeError:
            pass
    # fallback: one item per non-empty line
    return [ln.strip("-• ").strip() for ln in raw.splitlines() if ln.strip()]
