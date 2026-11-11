"""OCR engine interface (FR-EX-04, NFR-EX-05). Engines must work offline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class OcrLine:
    text: str
    confidence: float  # 0..1
    bbox: tuple[float, float, float, float]  # in PDF points


class OcrEngine(Protocol):
    name: str

    def version(self) -> str: ...

    def ocr(self, png: bytes, dpi: int) -> list[OcrLine]:
        """OCR one rendered page; bboxes are converted to PDF points (72 dpi)."""
        ...
