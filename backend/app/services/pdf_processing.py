"""PDF text extraction with automatic OCR fallback per page.

Real-world CBDT/GST notices are very often scanned images. We extract text
with PyMuPDF first; any page below the character threshold is rasterized
at 300 DPI and run through Tesseract (eng+hin).

System deps (add to Dockerfile):
    RUN apt-get update && apt-get install -y tesseract-ocr tesseract-ocr-hin

Python deps: pymupdf, pytesseract, Pillow
"""
import io
import logging
from dataclasses import dataclass

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class PageText:
    page_number: int          # 1-indexed — matches what users see in citations
    text: str
    used_ocr: bool


def extract_pages(pdf_bytes: bytes) -> list[PageText]:
    settings = get_settings()
    pages: list[PageText] = []

    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            used_ocr = False

            if len(text) < settings.ocr_min_chars_per_page:
                # Likely a scanned page — rasterize and OCR
                try:
                    pix = page.get_pixmap(dpi=300)
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    text = pytesseract.image_to_string(img, lang="eng+hin").strip()
                    used_ocr = True
                except Exception:
                    logger.exception("OCR failed on page %d", i)
                    text = text or ""

            pages.append(PageText(page_number=i, text=text, used_ocr=used_ocr))

    return pages


def document_is_empty(pages: list[PageText]) -> bool:
    return sum(len(p.text) for p in pages) < 50
