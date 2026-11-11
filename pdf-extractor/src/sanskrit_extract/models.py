"""Internal data types passed between pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class PageClass(StrEnum):
    TEXT_LAYER_OK = "text_layer_ok"
    TEXT_LAYER_BROKEN = "text_layer_broken"
    LEGACY_FONT = "legacy_font"
    IMAGE_ONLY = "image_only"


@dataclass(frozen=True)
class Span:
    text: str
    font: str  # subset prefix ("ABCDEE+") removed
    size: float


@dataclass(frozen=True)
class RawLine:
    """One printed line as found in the PDF text layer."""

    spans: tuple[Span, ...]
    bbox: tuple[float, float, float, float]

    @property
    def text(self) -> str:
        return "".join(s.text for s in self.spans)

    @property
    def size(self) -> float:
        sizes = [s.size for s in self.spans if s.text.strip()]
        return max(sizes) if sizes else 0.0


@dataclass(frozen=True)
class RawPage:
    number: int  # 1-based
    width: float
    height: float
    lines: tuple[RawLine, ...]
    image_coverage: float  # share of page area covered by images
    fonts: tuple[str, ...]
    rules: tuple[float, ...] = ()  # y of horizontal separator rules (thin, wide drawings), top to bottom


@dataclass
class Line:
    """One printed line after reading (text layer, legacy map or OCR), before normalization."""

    page: int
    text_raw: str  # exactly what the engine returned
    text: str  # Unicode text (decoded for legacy fonts; same as text_raw otherwise)
    bbox: tuple[float, float, float, float]
    size: float
    method: str  # text_layer | ocr | legacy_font_map
    tool: str
    tool_version: str
    ocr_confidence: float | None = None
    unknown_codes: list[str] = field(default_factory=list)


@dataclass
class PageResult:
    number: int
    width: float
    height: float
    page_class: PageClass
    lines: list[Line]
    rules: tuple[float, ...] = ()  # y of horizontal separator rules (text-layer pages only)
