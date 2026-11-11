"""Optional cross-check engine (extra `crosscheck`): an independent implementation to catch engine bugs."""

from __future__ import annotations

from importlib.metadata import version as _pkg_version

_SCHEMES = {"iast": "IAST", "iso15919": "ISO", "hk": "HK", "itrans": "Itrans", "slp1": "SLP1", "velthuis": "Velthuis"}


class AksharamukhaEngine:
    name = "aksharamukha"

    def version(self) -> str:
        return _pkg_version("aksharamukha")

    def from_devanagari(self, text: str, scheme: str) -> str:
        """Dandas are kept out of the engine and returned as `|`/`||`, the same as the default engine."""
        from aksharamukha import transliterate

        parts = text.replace("॥", "\ue020").replace("।", "\ue021")
        out = str(transliterate.process("Devanagari", _SCHEMES[scheme], parts))
        return out.replace("\ue020", "||").replace("\ue021", "|")

    def to_devanagari(self, text: str, scheme: str) -> str:
        from aksharamukha import transliterate

        return str(transliterate.process(_SCHEMES[scheme], "Devanagari", text))
