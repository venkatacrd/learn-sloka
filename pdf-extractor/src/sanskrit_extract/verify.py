"""Automatic OCR cross-check (FR-EX-20, Q11): a second, independent reading of each unit.

Each printed line of a unit that was read from the text layer or a legacy-font table is rendered and OCR'd on
its own, and the two readings are compared with whitespace removed. Clear disagreements are flagged; the unit's
text is never changed.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from rapidfuzz.distance import Levenshtein

from sanskrit_extract.config import Config
from sanskrit_extract.normalize import normalize
from sanskrit_extract.ocr.base import OcrEngine
from sanskrit_extract.pdf_reader import PdfDocument
from sanskrit_extract.segmenter import Unit
from sanskrit_extract.syllables import script_of

# only Devanagari letters and signs are compared; spacing, punctuation, digits and leader dots are ignored
_IGNORED = re.compile(r"[^\u0900-\u0963\u0970-\u097f]+")


def comparable(text: str, cfg: Config) -> str:
    return _IGNORED.sub("", unicodedata.normalize("NFC", normalize(text, cfg.normalize)))


@dataclass
class UnitCheck:
    cer: float
    ocr_text: str


def cer(reference: str, other: str) -> float:
    if not reference:
        return 0.0 if not other else 1.0
    return Levenshtein.distance(reference, other) / len(reference)


def check_units(doc: PdfDocument, units: list[Unit], engine: OcrEngine, cfg: Config) -> dict[int, UnitCheck]:
    """Return a check per unit index; adds flags to disagreeing units in place. OCR'd units are skipped."""
    v = cfg.verify
    out: dict[int, UnitCheck] = {}
    for i, unit in enumerate(units):
        if any(ln.method == "ocr" for ln in unit.lines):
            continue
        if script_of(" ".join(ln.text for ln in unit.lines)) != "devanagari":
            continue  # the OCR models are Sanskrit/Hindi; other scripts are out of scope (P2-02)
        ocr_lines = []
        for ln in unit.lines:
            png = doc.render_clip_png(ln.page, ln.bbox, v.dpi, v.padding)
            ocr_lines.append(" ".join(o.text for o in engine.ocr(png, v.dpi)))
        ocr_text = " ".join(ocr_lines)
        if not comparable(ocr_text, cfg):
            out[i] = UnitCheck(-1.0, "")  # OCR read nothing: not checked, not a disagreement
            continue
        ref = comparable(" ".join(ln.text for ln in unit.lines), cfg)
        score = round(cer(ref, comparable(ocr_text, cfg)), 4)
        out[i] = UnitCheck(score, normalize(ocr_text, cfg.normalize))
        if score > v.cer_threshold:
            unit.flags += ["ocr_disagreement", "needs_review"]
    return out


def report_block(checks: dict[int, UnitCheck], unit_ids: list[str], engine_name: str, cfg: Config) -> dict[str, Any]:
    scores = [c.cer for c in checks.values() if c.cer >= 0]
    bad = {i: c for i, c in checks.items() if c.cer > cfg.verify.cer_threshold}
    unread = [unit_ids[i] for i, c in sorted(checks.items()) if c.cer < 0]
    return {
        "engine": engine_name,
        "cer_threshold": cfg.verify.cer_threshold,
        "units_checked": len(scores),
        "units_ocr_empty": unread,  # OCR returned no text for these; they were not checked
        "units_disagreeing": len(bad),
        "mean_cer": round(sum(scores) / len(scores), 4) if scores else None,
        "max_cer": max(scores) if scores else None,
        "disagreements": [
            {"unit_id": unit_ids[i], "cer": c.cer, "ocr_text": c.ocr_text} for i, c in sorted(bad.items())
        ],
    }
