"""Devanagari ratio and syllable validity (FR-EX-02, FR-EX-12)."""

from __future__ import annotations

import re

DEVA_LETTER = re.compile(r"[ऄ-हऽॐक़-ॡॲ-ॿ]")
ANY_LETTER = re.compile(r"[^\W\d_]")
LATIN_LETTER = re.compile(r"[A-Za-zÀ-ɏ]")
DEVA_CHAR = re.compile(r"[ऀ-ॿ꣠-ꣿ᳐-᳿]")

_C = "[क-हक़-य़ॸ-ॿ]़?"
_V = "[ऄ-औॠॡॲ-ॷ]"
_MATRA = "[ऺऻा-ौॎॏॕ-ॗॢॣ]"
_MOD = "[ऀ-ः॑-॔᳐-᳿꣠-꣱]"
_VIRAMA = "्"
_OTHER = "[ऽॐ।॥०-९॰ॱ]"
# one valid orthographic syllable, or a standalone sign
# a syllable carries at most one vowel sign
_SYLLABLE = re.compile(f"(?:{_C}{_VIRAMA}[‌‍]?)*{_C}(?:{_VIRAMA}[‌‍]?|{_MATRA}?){_MOD}*|{_V}{_MOD}*|{_OTHER}{_MOD}*")
_RUN = re.compile(r"[ऀ-ॿ᳐-᳿꣠-ꣿ‌‍]+")


def deva_ratio(text: str) -> float:
    """Devanagari letters / all letters. 1.0 when there are no letters."""
    letters = ANY_LETTER.findall(text)
    if not letters:
        return 1.0
    deva = sum(1 for ch in letters if DEVA_LETTER.match(ch))
    return deva / len(letters)


def syllable_validity(text: str) -> float:
    """Share of Devanagari characters that belong to a well-formed syllable. 1.0 when none."""
    total = valid = 0
    for run in _RUN.finditer(text):
        s = run.group()
        total += len(s)
        pos = 0
        while pos < len(s):
            m = _SYLLABLE.match(s, pos)
            if m and m.end() > pos:
                valid += m.end() - pos
                pos = m.end()
            else:
                pos += 1  # invalid char (e.g. a matra with no consonant before it)
    return valid / total if total else 1.0


def script_of(text: str) -> str:
    letters = ANY_LETTER.findall(text)
    if not letters:
        return "unknown"
    deva = sum(1 for ch in letters if DEVA_LETTER.match(ch))
    latin = sum(1 for ch in letters if LATIN_LETTER.match(ch))
    if deva / len(letters) >= 0.9:
        return "devanagari"
    if latin / len(letters) >= 0.9:
        return "latin"
    return "mixed"
