"""Page-aware chunking. Chunks never cross page boundaries so that every
chunk maps to exactly one page number — this is what makes [Page X]
citations trustworthy. ~800 chars with 100 char overlap per the plan.
"""
from dataclasses import dataclass

from app.core.config import get_settings
from app.services.pdf_processing import PageText


@dataclass
class Chunk:
    chunk_index: int
    page_number: int
    content: str


def _split_page(text: str, size: int, overlap: int) -> list[str]:
    text = " ".join(text.split())  # normalize whitespace
    if not text:
        return []
    if len(text) <= size:
        return [text]

    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        # try to break on sentence/word boundary near the end
        if end < len(text):
            for sep in (". ", "। ", "\n", " "):  # '।' = Hindi danda
                cut = text.rfind(sep, start + int(size * 0.6), end)
                if cut != -1:
                    end = cut + len(sep)
                    break
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [c for c in chunks if c]


def chunk_pages(pages: list[PageText]) -> list[Chunk]:
    s = get_settings()
    out: list[Chunk] = []
    idx = 0
    for page in pages:
        for piece in _split_page(page.text, s.chunk_size, s.chunk_overlap):
            out.append(Chunk(chunk_index=idx, page_number=page.page_number, content=piece))
            idx += 1
    return out
