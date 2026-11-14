"""Library API (FR-TR-13): the same code path as batch mode."""

from __future__ import annotations

from sanskrit_romanize import accents
from sanskrit_romanize.config import Config
from sanskrit_romanize.engines.base import TransliterationEngine
from sanskrit_romanize.engines.sanscript_engine import SanscriptEngine
from sanskrit_romanize.postprocess import after_engine, ascii_fold, mark_hiatus
from sanskrit_romanize.script_runs import segments

_DEFAULT = SanscriptEngine()


def romanize(
    text: str, scheme: str = "iast", config: Config | None = None, engine: TransliterationEngine | None = None
) -> str:
    """Devanagari → `scheme` (iast, iso15919, hk, itrans, slp1, velthuis, the lossy ascii, or the telugu script).

    Latin words in the text (e.g. a Roman page number) are kept exactly as they are (FR-TR-08).
    """
    cfg = config or Config()
    eng = engine or _DEFAULT
    if scheme == "ascii":
        return ascii_fold(romanize(text, "iast", cfg, eng))
    return "".join(part if latin else _romanize_part(part, scheme, cfg, eng) for latin, part in segments(text))


def _romanize_part(text: str, scheme: str, cfg: Config, eng: TransliterationEngine) -> str:
    raw = eng.from_devanagari(accents.protect(mark_hiatus(text)), scheme)
    return accents.restore(after_engine(raw, scheme, cfg))
