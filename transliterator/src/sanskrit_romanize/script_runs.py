"""Script handling (FR-TR-08): Devanagari parts are romanized, Latin words are kept as they are."""

from __future__ import annotations

import re
from typing import Any

_DEVA = re.compile(r"[\u0900-\u097f]")
# a Latin word or run of words (e.g. a Roman page number "i", or "Chapter One")
_LATIN_RUN = re.compile(r"[A-Za-z\u00c0-\u024f]+(?:['\u2019\s]+[A-Za-z\u00c0-\u024f]+)*")


def has_devanagari(unit: dict[str, Any]) -> bool:
    return bool(_DEVA.search(str(unit["text"])))


def has_latin(text: str) -> bool:
    return bool(_LATIN_RUN.search(text))


def segments(text: str) -> list[tuple[bool, str]]:
    """Split into (is_latin, part); joining the parts gives back `text` exactly."""
    out: list[tuple[bool, str]] = []
    pos = 0
    for m in _LATIN_RUN.finditer(text):
        if m.start() > pos:
            out.append((False, text[pos : m.start()]))
        out.append((True, m.group()))
        pos = m.end()
    if pos < len(text):
        out.append((False, text[pos:]))
    return out
