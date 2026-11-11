"""Romanize one extracted unit into a romanized-unit record."""

from __future__ import annotations

from typing import Any

from sanskrit_romanize import ROMANIZED_SCHEMA_VERSION, accents, rag_view, roundtrip
from sanskrit_romanize.api import romanize
from sanskrit_romanize.config import Config
from sanskrit_romanize.engines.base import TransliterationEngine
from sanskrit_romanize.script_runs import has_devanagari, has_latin


def romanize_unit(
    ex: dict[str, Any],
    cfg: Config,
    engine: TransliterationEngine,
    cross_engine: TransliterationEngine | None = None,
) -> dict[str, Any]:
    schemes = ["iast", *[s for s in cfg.schemes if s != "iast"]]
    warnings: list[str] = []
    skipped = not has_devanagari(ex)
    if skipped:
        romanized = dict.fromkeys(schemes, ex["text"])
        lines = {s: list(ex["lines"]) for s in schemes}
        warnings.append(f"skipped_not_devanagari (script={ex.get('script')})")
        ok = True
    else:
        romanized = {s: romanize(ex["text"], s, cfg, engine) for s in schemes}
        lines = {s: [romanize(ln, s, cfg, engine) for ln in ex["lines"]] for s in schemes}
        if accents.has_accents(ex["text"]):
            warnings.append("vedic_accents_unsupported")
        if has_latin(ex["text"]):
            warnings.append("latin_text_kept")
        problems = [roundtrip.check_source(ex["text"], engine, cfg)]
        problems += [roundtrip.check_source(src, engine, cfg) for src in ex["lines"]]
        found = [p for p in problems if p]
        warnings += found[:1]
        ok = not found
        if cross_engine is not None:
            other = romanize(ex["text"], "iast", cfg, cross_engine)
            if other != romanized["iast"]:
                warnings.append(f"cross_check_disagreement: {cross_engine.name} gives {other!r}")
    return {
        "romanized_schema_version": ROMANIZED_SCHEMA_VERSION,
        "extracted": ex,
        "romanized": romanized,
        "romanized_lines": lines,
        "transliteration": {
            "engine": engine.name,
            "engine_version": engine.version(),
            "roundtrip_ok": ok,
            "skipped": skipped,
            "warnings": warnings,
        },
        "rag": rag_view.build(ex, romanized, cfg.embedding_text),
    }
