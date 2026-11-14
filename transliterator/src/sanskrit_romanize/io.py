"""Read and validate input, write JSONL + report + readable text (FR-TR-01, 11, 14; NFR-TR-02)."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sanskrit_romanize.config import Config
from sanskrit_romanize.contracts import errors, validators
from sanskrit_romanize.engines.base import TransliterationEngine
from sanskrit_romanize.pages import PageSelection
from sanskrit_romanize.sloka_files import DUPLICATE_SLOKA_NUMBERS, collect, write_sloka_files
from sanskrit_romanize.unit import romanize_unit


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def find_inputs(path: Path) -> list[Path]:
    if path.is_dir():
        return sorted(p for p in path.rglob("*.jsonl") if not p.name.endswith(".romanized.jsonl"))
    return [path]


@dataclass
class FileResult:
    doc_id: str
    records: list[dict[str, Any]]
    report: dict[str, Any]
    invalid: list[dict[str, Any]] = field(default_factory=list)


def process_file(
    path: Path,
    cfg: Config,
    engine: TransliterationEngine,
    cross: TransliterationEngine | None = None,
    pages: PageSelection | None = None,
) -> FileResult:
    in_v, out_v = validators()
    records: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    outside = 0
    for no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            unit = json.loads(line)
        except json.JSONDecodeError as exc:
            invalid.append({"line": no, "error": f"bad JSON: {exc}"})
            continue
        errs = errors(in_v, unit)
        if errs:
            invalid.append({"line": no, "error": "; ".join(errs[:3])})
            continue
        src = unit["source"]
        if pages is not None and not pages.overlaps(src["page_start"], src["page_end"]):  # FR-TR-15
            outside += 1
            continue
        rec = romanize_unit(unit, cfg, engine, cross)
        out_errs = errors(out_v, rec)
        if out_errs:  # a bug on our side; never write an invalid record
            raise ValueError(f"{path.name} line {no}: output violates contract: {out_errs[:3]}")
        records.append(rec)
    doc_id = records[0]["extracted"]["doc_id"] if records else path.stem
    failed = [r for r in records if not r["transliteration"]["roundtrip_ok"]]
    # source text the extractor already flagged as invalid Devanagari cannot round-trip; not a pipeline loss
    source_invalid = [r for r in failed if "invalid_syllables" in r["extracted"]["quality"]["flags"]]
    failures = [r for r in failed if r not in source_invalid]
    report = {
        "doc_id": doc_id,
        "input": path.name,
        "units_in": len(records) + len(invalid),
        "units_out": len(records),
        "pages_selected": None if pages is None else pages.spec,
        "units_outside_pages": outside,
        "counts": dict(sorted(Counter(r["extracted"]["unit_type"] for r in records).items())),
        "roundtrip_ok": len(records) - len(failed),
        "roundtrip_failures": [
            {"unit_id": r["extracted"]["unit_id"], "warnings": r["transliteration"]["warnings"]} for r in failures
        ],
        "source_invalid": [
            {"unit_id": r["extracted"]["unit_id"], "warnings": r["transliteration"]["warnings"]} for r in source_invalid
        ],
        "skipped": [r["extracted"]["unit_id"] for r in records if r["transliteration"]["skipped"]],
        "invalid_lines": invalid,
        "schemes": ["iast", *[s for s in cfg.schemes if s != "iast"]],
        "engine": {"name": engine.name, "version": engine.version()},
    }
    return FileResult(doc_id, records, report, invalid)


def readable_text(records: list[dict[str, Any]]) -> str:
    """FR-TR-14: each unit's Devanagari lines, then Telugu (if produced), then IAST; a blank line between units."""
    if not records:
        return ""
    first = records[0]["extracted"]
    out = [f"# {first['source']['file_name']} ({first['doc_id']})", ""]
    for r in records:
        ex = r["extracted"]
        label = ex["unit_type"] + (f" {ex['verse_ref']['normalized']}" if ex.get("verse_ref") else "")
        mark = "" if r["transliteration"]["roundtrip_ok"] else "  [ROUND-TRIP FAILED]"
        out.append(f"[{label} · p.{ex['source']['page_start']}]{mark}")
        out += ex["lines"]
        out += r["romanized_lines"].get("telugu", [])
        out += r["romanized_lines"]["iast"]
        out.append("")
    return "\n".join(out)


def write(
    outdir: Path,
    result: FileResult,
    sloka_prefix: str | None = None,
    sloka_dir: Path | None = None,
    sloka_source: bool = True,
) -> list[Path]:
    """Write JSONL, report and readable text; with sloka_prefix also one file per sloka (FR-TR-16)."""
    outdir.mkdir(parents=True, exist_ok=True)
    sloka_paths: list[Path] = []
    if sloka_prefix is not None:
        found = collect(result.records)
        block: dict[str, Any] = {
            "folder": str(sloka_dir or outdir / "slokas"),
            "prefix": sloka_prefix,
            "written": 0,
            "source_text": sloka_source,
            "skipped": found.skipped,
        }
        if found.duplicates:
            block["error"] = DUPLICATE_SLOKA_NUMBERS
            block["duplicate_numbers"] = found.duplicates
        else:
            sloka_paths = write_sloka_files(sloka_dir or outdir / "slokas", sloka_prefix, found.slokas, sloka_source)
            block["written"] = len(sloka_paths)
        result.report["sloka_files"] = block
    paths = [outdir / f"{result.doc_id}.romanized{ext}" for ext in (".jsonl", ".report.json", ".txt")]
    paths[0].write_text("".join(dumps(r) + "\n" for r in result.records), encoding="utf-8", newline="\n")
    paths[1].write_text(
        json.dumps(result.report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    paths[2].write_text(readable_text(result.records), encoding="utf-8", newline="\n")
    return paths + sloka_paths
