"""Default engine: indic-transliteration (sanscript)."""

from __future__ import annotations

from importlib.metadata import version as _pkg_version

from indic_transliteration import sanscript

_SCHEMES = {
    "iast": sanscript.IAST,
    "iso15919": sanscript.ISO,
    "hk": sanscript.HK,
    "itrans": sanscript.ITRANS,
    "slp1": sanscript.SLP1,
    "velthuis": sanscript.VELTHUIS,
    "telugu": sanscript.TELUGU,  # a script, not a romanization (FR-TR-19)
}


class SanscriptEngine:
    name = "indic-transliteration"

    def version(self) -> str:
        return _pkg_version("indic-transliteration")

    def from_devanagari(self, text: str, scheme: str) -> str:
        return str(sanscript.transliterate(text, sanscript.DEVANAGARI, _SCHEMES[scheme]))

    def to_devanagari(self, text: str, scheme: str) -> str:
        return str(sanscript.transliterate(text, _SCHEMES[scheme], sanscript.DEVANAGARI))
