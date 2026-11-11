"""Per-document flow: read → classify → (map | OCR) → layout → normalize → segment → score → records."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sanskrit_extract import SCHEMA_VERSION, legacy_fonts
from sanskrit_extract.config import Config
from sanskrit_extract.layout import remove_headers_footers
from sanskrit_extract.models import Line, PageClass, PageResult, RawLine, RawPage
from sanskrit_extract.normalize import normalize
from sanskrit_extract.ocr.base import OcrEngine
from sanskrit_extract.page_classifier import classify, legacy_fonts_on
from sanskrit_extract.pages import Pages, resolve
from sanskrit_extract.pdf_reader import TOOL, TOOL_VERSION, PdfDocument, sha256_of
from sanskrit_extract.quality import assess
from sanskrit_extract.segmenter import Segmenter, Unit
from sanskrit_extract.syllables import DEVA_CHAR, script_of, syllable_validity
from sanskrit_extract.verify import check_units, report_block
from sanskrit_extract.writer import write_outputs

EngineFactory = Callable[[], OcrEngine]


def doc_id_for(path: Path, sha256: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-") or "doc"
    return f"{slug}-{sha256[:8]}"


@dataclass
class PagePlan:
    number: int
    page_class: PageClass
    needs_ocr: bool


@dataclass
class DocResult:
    doc_id: str
    units: list[dict[str, Any]]
    report: dict[str, Any]
    ocr_calls: int = 0


def _broken_line(ln: RawLine, cfg: Config) -> bool:
    """A non-legacy line on a legacy page whose own text layer is unreadable (FR-EX-02)."""
    if any(legacy_fonts.get(s.font) for s in ln.spans):
        return False
    text = ln.text
    return bool(DEVA_CHAR.search(text)) and syllable_validity(text) < cfg.classifier.syllable_validity_min


def _needs_ocr(raw: RawPage, cls: PageClass, cfg: Config) -> bool:
    """Whole page goes to OCR."""
    if cfg.force_ocr or cls in (PageClass.IMAGE_ONLY, PageClass.TEXT_LAYER_BROKEN):
        return True
    if cls is PageClass.LEGACY_FONT:
        return any(legacy_fonts.get(f) is None for f in legacy_fonts_on(raw, cfg.classifier))
    return False


def _needs_line_ocr(raw: RawPage, cls: PageClass, cfg: Config) -> bool:
    return (
        cls is PageClass.LEGACY_FONT
        and not _needs_ocr(raw, cls, cfg)
        and any(_broken_line(ln, cfg) for ln in raw.lines)
    )


def plan_pages(doc: PdfDocument, cfg: Config, pages: Pages = None) -> list[PagePlan]:
    """Classify pages without OCR (used by --dry-run and the Tesseract check)."""
    out = []
    for raw in doc.pages(resolve(pages, doc.page_count)[0]):
        cls = classify(raw, cfg.classifier)
        out.append(PagePlan(raw.number, cls, _needs_ocr(raw, cls, cfg) or _needs_line_ocr(raw, cls, cfg)))
    return out


@dataclass
class _Reader:
    doc: PdfDocument
    cfg: Config
    engine_factory: EngineFactory
    line_engine_factory: EngineFactory | None = None
    _engine: OcrEngine | None = None
    _line_engine: OcrEngine | None = None
    ocr_calls: int = 0
    unknown: Counter[str] = field(default_factory=Counter)

    def engine(self) -> OcrEngine:
        if self._engine is None:
            self._engine = self.engine_factory()
        return self._engine

    def line_engine(self) -> OcrEngine:
        if self._line_engine is None:
            self._line_engine = (self.line_engine_factory or self.engine_factory)()
        return self._line_engine

    def read(self, raw: RawPage) -> PageResult:
        cls = classify(raw, self.cfg.classifier)
        if _needs_ocr(raw, cls, self.cfg):
            lines = self._ocr(raw)
        elif cls is PageClass.LEGACY_FONT:
            lines = self._legacy(raw)
        else:
            lines = [
                Line(raw.number, ln.text, ln.text, ln.bbox, ln.size, "text_layer", TOOL, TOOL_VERSION)
                for ln in raw.lines
            ]
        return PageResult(raw.number, raw.width, raw.height, cls, lines, raw.rules)

    def _legacy(self, raw: RawPage) -> list[Line]:
        lines = []
        for ln in raw.lines:
            parts: list[str] = []
            unknown: list[str] = []
            fmap = None
            for span in ln.spans:
                m = legacy_fonts.get(span.font)
                if m is None:
                    parts.append(span.text)
                else:
                    fmap = m
                    text, unk = m.decode(span.text)
                    parts.append(text)
                    unknown += unk
            self.unknown.update(unknown)
            if fmap is None and _broken_line(ln, self.cfg):
                lines.append(self._ocr_line(raw, ln))
            elif fmap is None:
                lines.append(Line(raw.number, ln.text, ln.text, ln.bbox, ln.size, "text_layer", TOOL, TOOL_VERSION))
            else:
                lines.append(
                    Line(
                        raw.number,
                        ln.text,
                        "".join(parts),
                        ln.bbox,
                        ln.size,
                        "legacy_font_map",
                        fmap.name,
                        fmap.version,
                        unknown_codes=unknown,
                    )
                )
        return lines

    def _ocr_line(self, raw: RawPage, ln: RawLine) -> Line:
        engine = self.line_engine()
        dpi = self.cfg.ocr.dpi
        self.ocr_calls += 1
        result = engine.ocr(self.doc.render_clip_png(raw.number, ln.bbox, dpi, self.cfg.verify.padding), dpi)
        text = " ".join(o.text for o in result)
        conf = round(sum(o.confidence for o in result) / len(result), 4) if result else 0.0
        return Line(raw.number, text, text, ln.bbox, 0.0, "ocr", engine.name, engine.version(), ocr_confidence=conf)

    def _ocr(self, raw: RawPage) -> list[Line]:
        engine = self.engine()
        dpi = self.cfg.ocr.dpi
        self.ocr_calls += 1
        result = engine.ocr(self.doc.render_png(raw.number, dpi), dpi)
        version = engine.version()
        return [
            Line(raw.number, o.text, o.text, o.bbox, 0.0, "ocr", engine.name, version, ocr_confidence=o.confidence)
            for o in result
        ]


def _record(unit: Unit, seq: int, doc_id: str, file_name: str, sha: str, cfg: Config) -> dict[str, Any]:
    first = unit.lines[0]
    confs = [ln.ocr_confidence for ln in unit.lines if ln.ocr_confidence is not None]
    ocr_conf = round(sum(confs) / len(confs), 4) if confs else None
    text = " ".join(ln.text for ln in unit.lines)
    score, flags = assess(
        text, ocr_conf, unit.flags, cfg.quality, unknown_codes=any(ln.unknown_codes for ln in unit.lines)
    )
    pages = [ln.page for ln in unit.lines]
    return {
        "schema_version": SCHEMA_VERSION,
        "doc_id": doc_id,
        "unit_id": f"{doc_id}:{seq:06d}",
        "seq": seq,
        "unit_type": unit.unit_type,
        "verse_ref": unit.verse_ref,
        "source": {"file_name": file_name, "sha256": sha, "page_start": min(pages), "page_end": max(pages)},
        "text_raw": "\n".join(ln.text_raw for ln in unit.lines),
        "text": text,
        "lines": [ln.text for ln in unit.lines],
        "script": script_of(text),
        "extraction": {"method": first.method, "tool": first.tool, "tool_version": first.tool_version},
        "quality": {"score": score, "ocr_confidence": ocr_conf, "flags": flags},
    }


def extract(
    path: Path,
    cfg: Config,
    engine_factory: EngineFactory,
    pages: Pages = None,
    verify_engine_factory: EngineFactory | None = None,
) -> DocResult:
    sha = sha256_of(path)
    doc_id = doc_id_for(path, sha)
    with PdfDocument(path) as doc:
        selected, missing = resolve(pages, doc.page_count)
        if selected is not None and not selected:  # FR-EX-21
            raise ValueError(f"none of the selected pages exist (the document has {doc.page_count} pages)")
        reader = _Reader(doc, cfg, engine_factory, verify_engine_factory)
        page_results = [reader.read(raw) for raw in doc.pages(selected)]
        lines_read = sum(len(p.lines) for p in page_results)
        page_results, removed = remove_headers_footers(page_results, cfg.profile)
        removed_lines = [{"page": ln.page, "text": ln.text_raw, "reason": reason} for ln, reason in removed]
        for page in page_results:
            for ln in page.lines:
                ln.text = normalize(ln.text, cfg.normalize)
            removed_lines += [
                {"page": ln.page, "text": ln.text_raw, "reason": "empty_after_cleanup"}
                for ln in page.lines
                if not ln.text
            ]
            page.lines = [ln for ln in page.lines if ln.text]
        units = Segmenter(cfg.profile).segment(page_results)
        lines_in_units = sum(len(u.lines) for u in units)
        verification = None
        if cfg.verify.enabled:
            vengine = (verify_engine_factory or engine_factory)()
            checks = check_units(doc, units, vengine, cfg)
            ids = [f"{doc_id}:{i:06d}" for i in range(1, len(units) + 1)]
            verification = report_block(checks, ids, f"{vengine.name} {vengine.version()}", cfg)
    records = [_record(u, i, doc_id, path.name, sha, cfg) for i, u in enumerate(units, start=1)]
    report = {
        "doc_id": doc_id,
        "file_name": path.name,
        "sha256": sha,
        "pages_selected": selected,  # FR-EX-21; null = all pages
        "pages_missing": missing,
        "pages": [
            {"page": p.number, "class": p.page_class.value, "method": p.lines[0].method if p.lines else None}
            for p in page_results
        ],
        "counts": dict(sorted(Counter(r["unit_type"] for r in records).items())),
        "coverage": {  # FR-EX-19: nothing read from the PDF is dropped silently
            "lines_read": lines_read,
            "lines_in_units": lines_in_units,
            "lines_removed": len(removed_lines),
            "unaccounted": lines_read - lines_in_units - len(removed_lines),
        },
        "removed_lines": removed_lines,
        "unknown_legacy_codes": dict(sorted(reader.unknown.items())),
        "ocr_pages": reader.ocr_calls,
        "verification": verification,  # FR-EX-20; null when --verify-ocr is off
        "flagged": [
            {"unit_id": r["unit_id"], "flags": r["quality"]["flags"]}
            for r in records
            if "needs_review" in r["quality"]["flags"]
        ],
    }
    return DocResult(doc_id, records, report, reader.ocr_calls)


@dataclass
class BatchResult:
    written: list[Path] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)


def find_pdfs(input_path: Path) -> list[Path]:
    if input_path.is_dir():
        return sorted(p for p in input_path.rglob("*") if p.suffix.lower() == ".pdf" and p.is_file())
    return [input_path]


def run_batch(
    input_path: Path,
    outdir: Path,
    cfg: Config,
    engine_factory: EngineFactory,
    pages: Pages = None,
    verify_engine_factory: EngineFactory | None = None,
) -> BatchResult:
    """FR-EX-01: one bad file never stops the batch."""
    result = BatchResult()
    for pdf in find_pdfs(input_path):
        try:
            doc = extract(pdf, cfg, engine_factory, pages, verify_engine_factory)
        except Exception as exc:
            result.failed[str(pdf)] = f"{type(exc).__name__}: {exc}"
            continue
        write_outputs(outdir, doc.doc_id, doc.units, doc.report)
        result.written.append(outdir / f"{doc.doc_id}.jsonl")
    return result
