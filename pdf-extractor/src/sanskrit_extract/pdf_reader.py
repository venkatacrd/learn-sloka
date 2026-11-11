"""PyMuPDF wrapper: pages, lines with fonts and positions, page rendering."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pymupdf

from sanskrit_extract.models import RawLine, RawPage, Span

TOOL = "pymupdf"
TOOL_VERSION: str = pymupdf.VersionBind


class PdfError(Exception):
    """The file is not a readable PDF (corrupt, encrypted, ...)."""


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _font_name(name: str) -> str:
    return name.split("+", 1)[1] if "+" in name[:8] else name


def _horizontal_rules(page: Any) -> tuple[float, ...]:
    """y positions of thin horizontal lines at least 30 % of the page wide (header/footer separators)."""
    width = float(page.rect.width)
    ys = set()
    for d in page.get_drawings():
        r = d["rect"]
        if r.height <= 3.0 and r.width >= 0.3 * width:
            ys.add(round(float(r.y0 + r.y1) / 2, 1))
    return tuple(sorted(ys))


class PdfDocument:
    def __init__(self, path: Path) -> None:
        try:
            self._doc: Any = pymupdf.open(path)
        except Exception as exc:  # PyMuPDF raises several types for bad files
            raise PdfError(f"cannot open: {exc}") from exc
        if self._doc.needs_pass:
            self._doc.close()
            raise PdfError("encrypted")
        if not self._doc.is_pdf:
            self._doc.close()
            raise PdfError("not a PDF")
        self.path = path

    @property
    def page_count(self) -> int:
        return int(self._doc.page_count)

    def close(self) -> None:
        self._doc.close()

    def __enter__(self) -> PdfDocument:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def page(self, number: int) -> RawPage:
        """Read one page (1-based). Lines keep the PDF's own order (FR-EX-03)."""
        page = self._doc[number - 1]
        rect = page.rect
        lines: list[RawLine] = []
        for block in page.get_text("dict", sort=False)["blocks"]:
            for line in block.get("lines", []):
                spans = tuple(
                    Span(text=s["text"], font=_font_name(s["font"]), size=round(float(s["size"]), 1))
                    for s in line["spans"]
                )
                if "".join(s.text for s in spans).strip():
                    x0, y0, x1, y1 = (round(float(v), 2) for v in line["bbox"])
                    lines.append(RawLine(spans=spans, bbox=(x0, y0, x1, y1)))
        area = float(rect.width * rect.height) or 1.0
        covered = 0.0
        for info in page.get_image_info():
            b = pymupdf.Rect(info["bbox"]) & rect
            covered += float(b.width * b.height) if not b.is_empty else 0.0
        fonts = tuple(sorted({_font_name(f[3]) for f in page.get_fonts()}))
        return RawPage(
            rules=_horizontal_rules(page),
            number=number,
            width=float(rect.width),
            height=float(rect.height),
            lines=tuple(lines),
            image_coverage=min(covered / area, 1.0),
            fonts=fonts,
        )

    def pages(self, selected: list[int] | None = None) -> Iterator[RawPage]:
        for n in range(1, self.page_count + 1) if selected is None else selected:
            if 1 <= n <= self.page_count:
                yield self.page(n)

    def render_clip_png(self, number: int, bbox: tuple[float, float, float, float], dpi: int, pad: float) -> bytes:
        page = self._doc[number - 1]
        x0, y0, x1, y1 = bbox
        clip = pymupdf.Rect(x0 - pad, y0 - pad, x1 + pad, y1 + pad) & page.rect
        pix = page.get_pixmap(dpi=dpi, clip=clip, colorspace=pymupdf.csGRAY)
        return bytes(pix.tobytes("png"))

    def render_png(self, number: int, dpi: int) -> bytes:
        pix = self._doc[number - 1].get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
        return bytes(pix.tobytes("png"))
