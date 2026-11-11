"""Quality score and flags per unit (FR-EX-12, FR-EX-13)."""

from __future__ import annotations

import re

from sanskrit_extract.config import QualityConfig
from sanskrit_extract.syllables import deva_ratio, syllable_validity

VEDIC_ACCENTS = re.compile("[॑-॔᳐-᳿]")
FLAG_ORDER = (
    "low_ocr_confidence",
    "invalid_syllables",
    "legacy_font",
    "vedic_accents_present",
    "vedic_accents_possibly_lost",
    "crosses_page",
    "unnumbered_verse",
    "split_by_speaker",
    "ocr_disagreement",
    "needs_review",
)


def assess(
    text: str,
    ocr_confidence: float | None,
    flags: list[str],
    cfg: QualityConfig,
    unknown_codes: bool = False,
) -> tuple[float, list[str]]:
    """Return (score, sorted unique flags). score = weakest of the signals (plan.md)."""
    validity = syllable_validity(text)
    score = min(deva_ratio(text), validity, ocr_confidence if ocr_confidence is not None else 1.0)
    out = set(flags)
    if validity < 1.0:
        out.add("invalid_syllables")
    if unknown_codes:
        out |= {"legacy_font", "needs_review"}
    if ocr_confidence is not None and ocr_confidence < cfg.low_ocr_confidence_below:
        out |= {"low_ocr_confidence", "needs_review"}
    if VEDIC_ACCENTS.search(text):
        out |= {"vedic_accents_present", "needs_review"}
    if score < cfg.needs_review_below:
        out.add("needs_review")
    return round(score, 4), [f for f in FLAG_ORDER if f in out]
