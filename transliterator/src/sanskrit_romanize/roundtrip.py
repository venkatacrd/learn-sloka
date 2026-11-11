"""Round-trip check (FR-TR-07): IAST → Devanagari must give back the source text."""

from __future__ import annotations

import unicodedata

from sanskrit_romanize import accents
from sanskrit_romanize.config import Config
from sanskrit_romanize.engines.base import TransliterationEngine
from sanskrit_romanize.postprocess import HIATUS, before_reverse

_TO_ASCII = str.maketrans("०१२३४५६७८९", "0123456789")


def to_devanagari(iast: str, engine: TransliterationEngine, cfg: Config) -> str:
    text = accents.protect(before_reverse(iast, cfg))
    dev = engine.to_devanagari(text, "iast").replace(HIATUS, "")
    return unicodedata.normalize("NFC", accents.restore(dev))


def check(source: str, iast: str, engine: TransliterationEngine, cfg: Config) -> str | None:
    """None when lossless; otherwise a warning naming the first differing position."""
    back = to_devanagari(iast, engine, cfg)
    a = unicodedata.normalize("NFC", source)
    if cfg.digits == "ascii":  # digit script is a documented convention, not a loss of content
        a, back = a.translate(_TO_ASCII), back.translate(_TO_ASCII)
    if a == back:
        return None
    pos = next((i for i, (x, y) in enumerate(zip(a, back, strict=False)) if x != y), min(len(a), len(back)))
    return f"roundtrip_mismatch at {pos}: source {a[pos : pos + 8]!r} vs back {back[pos : pos + 8]!r}"


def check_source(source: str, engine: TransliterationEngine, cfg: Config) -> str | None:
    """Round-trip every Devanagari part of `source` (Latin words are kept as-is and need no check)."""
    from sanskrit_romanize.api import romanize
    from sanskrit_romanize.script_runs import segments

    offset = 0
    for latin, part in segments(source):
        if not latin:
            problem = check(part, romanize(part, "iast", cfg, engine), engine, cfg)
            if problem:
                pos = int(problem.split(" at ", 1)[1].split(":", 1)[0])
                return problem.replace(f" at {pos}:", f" at {offset + pos}:", 1)
        offset += len(part)
    return None
