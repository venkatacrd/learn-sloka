"""Validated configuration and segmentation profiles (FR-EX-16)."""

from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import BaseModel, Field

from sanskrit_extract.normalize import NormalizeConfig


class ClassifierConfig(BaseModel):
    image_coverage_min: float = 0.5
    deva_ratio_min: float = 0.3
    syllable_validity_min: float = 0.95
    legacy_fonts: list[str] = Field(default_factory=lambda: ["Sanskrit99"])


class Profile(BaseModel):
    """Per-book segmentation overrides."""

    # a line ending with this pattern closes a verse; group "num" = verse number (optional)
    verse_end: str = r"(?:॥\s*(?P<num>[०-९0-9]+(?:[.\-–][०-९0-9]+)*)\s*॥?|(?P<ascii>\b\d+\.\d+)|॥)\s*$"
    # no \b in Devanagari patterns: vowel signs are not "word" characters for `re`
    speaker: str = r"(?:^|\s)उवाच\s*[-:।]?\s*$"
    colophon_start: str = r"^(?:॥\s*)?(?:ॐ\s+)?(?:तत्सदिति|इति)(?:\s|$)"  # may continue on following lines
    colophon_end: str = r"[अऽ]ध्यायः\s*॥?\s*$"
    title_max_words: int = 3  # a lone short line outside a verse is a title
    header_zone: float = 0.08  # top/bottom share of page height checked for headers/footers
    repeat_min_share: float = 0.5  # FR-EX-08: repeated on ≥ 50 % of pages (or of the odd / even pages)
    rule_zone: float = 0.12  # top/bottom share of page height searched for header/footer separator rules
    small_font_ratio: float = 0.8  # a margin line this much smaller than body text ...
    small_font_min_pages: int = 2  # ... and repeated on this many pages is a running header/footer
    centered_tolerance: float = 0.06  # |line centre − page centre| / page width
    heading_max_width: float = 0.38  # headings are narrow; verse lines are wider (measured on the Gita PDFs)
    toc_entry: str = r"\.{4,}|…{2,}"  # leader dots of a table-of-contents line
    # an empty gap taller than factor × line height starts a new block (separates stray text from a verse)
    block_gap_factor: float = 0.75


class QualityConfig(BaseModel):
    needs_review_below: float = 0.85
    low_ocr_confidence_below: float = 0.75


class OcrConfig(BaseModel):
    dpi: int = 300
    languages: str = "san+hin"
    psm: int = 6
    cache_dir: Path | None = Path("~/.sanskrit-extract/ocr_cache").expanduser()


class VerifyConfig(BaseModel):
    """FR-EX-20: automatic OCR cross-check of units read from the text layer or a legacy-font table."""

    enabled: bool = False
    # Tesseract misreads ~10 % of characters on correct legacy-font text (up to ~27 % on short lines), so only
    # clear disagreements are flagged: a wrong/missing font table or a garbled page gives far higher rates.
    cer_threshold: float = 0.40
    dpi: int = 300
    psm: int = 7  # Tesseract: treat the image as a single text line
    padding: float = 3.0  # points around each line box


class Config(BaseModel):
    classifier: ClassifierConfig = Field(default_factory=ClassifierConfig)
    normalize: NormalizeConfig = Field(default_factory=NormalizeConfig)
    profile: Profile = Field(default_factory=Profile)
    quality: QualityConfig = Field(default_factory=QualityConfig)
    ocr: OcrConfig = Field(default_factory=OcrConfig)
    verify: VerifyConfig = Field(default_factory=VerifyConfig)
    force_ocr: bool = False


def load_config(path: Path | None = None, profile: Path | None = None) -> Config:
    data: dict[str, object] = {}
    if path is not None:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    cfg = Config.model_validate(data)
    if profile is not None:
        prof = tomllib.loads(profile.read_text(encoding="utf-8"))
        cfg.profile = Profile.model_validate(cfg.profile.model_dump() | prof)
    return cfg
