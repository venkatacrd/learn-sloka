"""Comparison form of Devanagari text (FR-RC-05).

Works on (character, owner) pairs so every compared letter can be traced back: for the expected text the owner
is the word index, for the heard text the index of the heard character (which carries time and probability).
"""

from __future__ import annotations

import re
import unicodedata

VIRAMA = "्"
ANUSVARA = "ं"
_DROP = re.compile(r"[\s।॥|\-0-9०-९.,'’ऽ‌]")
INDEPENDENT_TO_MATRA = {
    "अ": "",
    "आ": "ा",
    "इ": "ि",
    "ई": "ी",
    "उ": "ु",
    "ऊ": "ू",
    "ऋ": "ृ",
    "ए": "े",
    "ऐ": "ै",
    "ओ": "ो",
    "औ": "ौ",
}
# homorganic nasal for each class of consonants (nasal + virama before them == anusvara)
NASAL_CLASS = {
    "ङ": "कखगघ",
    "ञ": "चछजझ",
    "ण": "टठडढ",
    "न": "तथदध",
    "म": "पफबभ",
}

NON_CLASS = set("यरलवशषसह")  # before these, म् and anusvara are pronounced alike
SIGNS = set("ािीुूृॄेैोौॢॣ्ंःँ")

Chars = list[tuple[str, int]]


def chars_of(text: str, owner: int) -> Chars:
    return [(c, owner) for c in unicodedata.normalize("NFC", text)]


def comparison_form(chars: Chars) -> Chars:
    """Drop spaces/punctuation, join sandhi written as virama + independent vowel, anusvara before a consonant of a
    nasal class -> that class's nasal + virama (संग == सङ्ग), so the original conjunct letters are kept."""
    out: Chars = [(c, o) for c, o in chars if not _DROP.match(c)]
    # virama followed by an independent vowel: the consonant takes the vowel sign (पुत्राणाम् आचार्य -> पुत्राणामाचार्य)
    joined: Chars = []
    for c, o in out:
        if joined and joined[-1][0] == VIRAMA and c in INDEPENDENT_TO_MATRA:
            joined.pop()
            sign = INDEPENDENT_TO_MATRA[c]
            if sign:
                joined.append((sign, o))
            continue
        joined.append((c, o))
    final: Chars = []
    i = 0
    while i < len(joined):
        c, o = joined[i]
        nxt = joined[i + 1][0] if i + 1 < len(joined) else ""
        nasal = next((n for n, cls in NASAL_CLASS.items() if nxt and nxt in cls), None)
        if c == ANUSVARA and nasal:
            final += [(nasal, o), (VIRAMA, o)]
        elif c == "म" and nxt == VIRAMA and i + 2 < len(joined) and joined[i + 2][0] in NON_CLASS:
            final.append((ANUSVARA, o))  # म्य == ंय (उपसङ्गम्य == उपसङ्गंय)
            i += 1
        elif final and c in SIGNS and final[-1][0] == c:
            pass  # the model sometimes repeats a vowel sign (मिि): one sign
        else:
            final.append((c, o))
        i += 1
    return final


def text_of(chars: Chars) -> str:
    return "".join(c for c, _ in chars)
