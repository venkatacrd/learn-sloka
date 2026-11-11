"""Vedic accents (FR-TR-06, Phase 1): keep the marks unchanged through transliteration."""

from __future__ import annotations

import re

ACCENTS = re.compile("[॑-॔᳐-᳿]")
_BASE = 0xE100  # private-use placeholders the engine passes through untouched


def has_accents(text: str) -> bool:
    return bool(ACCENTS.search(text))


def protect(text: str) -> str:
    return ACCENTS.sub(
        lambda m: chr(
            _BASE + ord(m.group()) - 0x0900 if ord(m.group()) < 0x1000 else _BASE + 0x100 + ord(m.group()) - 0x1CD0
        ),
        text,
    )


def restore(text: str) -> str:
    def back(m: re.Match[str]) -> str:
        n = ord(m.group()) - _BASE
        return chr(0x0900 + n) if n < 0x100 else chr(0x1CD0 + n - 0x100)

    return re.sub("[-]", back, text)
