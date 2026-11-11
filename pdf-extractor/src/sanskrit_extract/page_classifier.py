"""Page classification (FR-EX-02). See plan.md 'Page classification'."""

from __future__ import annotations

from sanskrit_extract.config import ClassifierConfig
from sanskrit_extract.models import PageClass, RawPage
from sanskrit_extract.syllables import deva_ratio, syllable_validity


def legacy_fonts_on(page: RawPage, cfg: ClassifierConfig) -> list[str]:
    known = {f.lower() for f in cfg.legacy_fonts}
    return sorted({s.font for line in page.lines for s in line.spans if s.font.lower() in known})


def classify(page: RawPage, cfg: ClassifierConfig) -> PageClass:
    text = "\n".join(line.text for line in page.lines)
    if not text.strip():
        return PageClass.IMAGE_ONLY
    if legacy_fonts_on(page, cfg):
        return PageClass.LEGACY_FONT  # other-font lines on it are routed per line (FR-EX-02)
    if deva_ratio(text) < cfg.deva_ratio_min:
        if page.image_coverage > cfg.image_coverage_min:
            return PageClass.IMAGE_ONLY  # only a stray text overlay (e.g. page number) on a scan
        return PageClass.TEXT_LAYER_BROKEN
    if syllable_validity(text) < cfg.syllable_validity_min:
        return PageClass.TEXT_LAYER_BROKEN
    return PageClass.TEXT_LAYER_OK
