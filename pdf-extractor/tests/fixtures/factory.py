"""Fixture factory (EX-T03): generate PDFs from known Unicode strings.

`insert_text` writes the exact string into the text layer (no shaping), so extraction can be checked
character for character. Image-only pages are made by rasterizing a text page.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pymupdf
import pytest

FONT_FILE = Path("/System/Library/Fonts/Supplemental/DevanagariMT.ttc")
PAGE_W, PAGE_H = 595.0, 842.0
GOLD_DIR = Path(__file__).parent / "gold"


def gold(name: str) -> str:
    return (GOLD_DIR / f"{name}.txt").read_text(encoding="utf-8").strip()


def require_font() -> None:
    if not FONT_FILE.exists():
        pytest.skip("Devanagari system font not available")


@dataclass(frozen=True)
class T:
    """A text line at (x, y); x=None centres it."""

    text: str
    y: float
    x: float | None = 60.0
    size: float = 14.0
    latin: bool = False  # use a built-in Latin font (the Devanagari font has no Latin letters)


@dataclass(frozen=True)
class Rule:
    """A thin horizontal separator line across the page at height y."""

    y: float


@dataclass(frozen=True)
class Image:
    """A page that holds only a picture of these lines (a 'scan')."""

    lines: tuple[T, ...]


PageSpec = list[T | Rule] | Image


def _draw(page: Any, lines: list[T | Rule] | tuple[T, ...]) -> None:
    page.insert_font(fontname="dv", fontfile=str(FONT_FILE))
    font = pymupdf.Font(fontfile=str(FONT_FILE))
    for ln in lines:
        if isinstance(ln, Rule):
            page.draw_line((40, ln.y), (PAGE_W - 40, ln.y), width=0.75)
            continue
        f = pymupdf.Font("helv") if ln.latin else font
        x = ln.x if ln.x is not None else (PAGE_W - f.text_length(ln.text, ln.size)) / 2
        page.insert_text((x, ln.y), ln.text, fontname="helv" if ln.latin else "dv", fontsize=ln.size)


def make_pdf(path: Path, pages: list[PageSpec]) -> Path:
    require_font()
    doc = pymupdf.open()
    for spec in pages:
        page = doc.new_page(width=PAGE_W, height=PAGE_H)
        if isinstance(spec, Image):
            tmp = pymupdf.open()
            tp = tmp.new_page(width=PAGE_W, height=PAGE_H)
            _draw(tp, spec.lines)
            pix = tp.get_pixmap(dpi=150)
            page.insert_image(page.rect, stream=pix.tobytes("png"))
        else:
            _draw(page, spec)
    doc.save(path, deflate=True, garbage=3, no_new_id=True)
    return path


def verse_lines(n: int, y: float, x: float = 60.0) -> list[T]:
    """Two printed lines of a made-up verse numbered n (Devanagari digits)."""
    num = str(n).translate(str.maketrans("0123456789", "०१२३४५६७८९"))
    return [T("धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः ।", y, x), T(f"मामकाः पाण्डवाश्चैव किमकुर्वत सञ्जय ॥ {num} ॥", y + 20, x)]


class FakeEngine:
    """Offline stand-in for Tesseract: returns fixed lines and counts calls."""

    name = "tesseract"

    def __init__(self, lines: list[tuple[str, float]] | None = None) -> None:
        self.calls = 0
        self.lines = lines or [("धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः ।", 0.95), ("मामकाः पाण्डवाश्चैव किमकुर्वत सञ्जय ॥ १ ॥", 0.95)]

    def version(self) -> str:
        return "fake-5.0"

    def ocr(self, png: bytes, dpi: int) -> list[Any]:
        from sanskrit_extract.ocr.base import OcrLine

        self.calls += 1
        return [OcrLine(t, c, (60.0, 100.0 + 20 * i, 400.0, 116.0 + 20 * i)) for i, (t, c) in enumerate(self.lines)]
