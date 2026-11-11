"""Sanskrit99 → Unicode Devanagari (FR-EX-05, Q9).

Sanskrit99 is a pre-Unicode font: each Devanagari shape sits on a Latin code point, in *visual* order.
Decoding is a longest-match table lookup followed by two reorderings:

* the short-i sign `ि` is stored *before* the consonant cluster it belongs to → move it after the cluster;
* the reph (`र्` written above) is stored *after* the syllable it belongs to → move it before that syllable.

Codes not in the table are kept and reported, never guessed (constitution 6).
"""

from __future__ import annotations

import re
import unicodedata

NAME = "sanskrit99"
VERSION = "1.1.0"  # 1.1.0: 52 codes added from the full Gita PDF (each checked against the rendered page)

_I_MARK = ""  # placeholder for prefix short-i
_REPH = ""  # placeholder for reph
_VIRAMA = "्"

# Longest keys first is handled by the regex built below.
TABLE: dict[str, str] = {
    # independent vowels (built from A + matra shapes)
    "AaE": "औ",
    "Aae": "ओ",
    "Aa": "आ",
    "A": "अ",
    "#": "इ",
    "%": "उ",
    "@e": "ऐ",
    "@": "ए",
    # vowel signs
    # "Ea": the same ौ shape keyed in reverse order (seen in the reference PDF)
    "aE": "ौ",
    "Ea": "ौ",
    "ae": "ो",
    "a": "ा",
    "i": _I_MARK,
    "I": "ी",
    "u": "ु",
    "U": "ू",
    "…": "ु",
    "‚": "ु",
    "&": "ृ",
    "«": "ृ",
    "¨": "ॄ",
    "e": "े",
    "E": "ै",
    # modifiers and signs
    "<": "ं",
    "—": "ं",
    ">": "ः",
    "!": _VIRAMA,
    "œ": _VIRAMA,
    "=": "ऽ",
    "`": "ॐ",
    "R": _REPH,
    "¡": _REPH + "ं",
    "+": _VIRAMA + "र",  # subscript ra (e.g. ष्ट्र, ण्ड्र)
    # punctuation and digits
    ",": "।",
    ".": "॥",
    "0": "०",
    "1": "१",
    "2": "२",
    "3": "३",
    "4": "४",
    "5": "५",
    "6": "६",
    "7": "७",
    "8": "८",
    "9": "९",
    # full consonants
    "k": "क",
    "o": "ख",
    "g": "ग",
    '"': "घ",
    "'": "ङ",
    "c": "च",
    "D": "छ",
    "j": "ज",
    "}": "ज्ञ",
    "q": "ट",
    "f": "ड",
    "F": "ढ",
    "[": "ण",
    "t": "त",
    "w": "थ",
    "d": "द",
    "x": "ध",
    "n": "न",
    "p": "प",
    "b": "ब",
    "É": "भ",
    "m": "म",
    "y": "य",
    "r": "र",
    "l": "ल",
    "v": "व",
    "z": "श",
    ";": "ष",
    "s": "स",
    "h": "ह",
    "]": "क्ष",
    # half forms (consonant + virama)
    "K": "क्",
    "O": "ख्",
    "C": "च्",
    "J": "ज्",
    "{": "ण्",
    "T": "त्",
    "X": "ध्",
    "N": "न्",
    "P": "प्",
    "B": "ब्",
    "M": "म्",
    "V": "व्",
    "Z": "श्",
    ":": "ष्",
    "S": "स्",
    "ú": "क्ष्",
    # conjunct and special ligatures
    "Ç": "त्र",
    "à": "प्र",
    "ä": "ब्र",
    "æ": "भ्र",
    "ö": "स्र",
    "ô": "स्त्र",
    "Ô": "द्र",
    "³": "क्र",
    "´": "क्त",
    "®": "क्त्",
    "²": "क्न",
    "‹": "क्च",
    "¶": "ग्न",
    "¹": "घ्न",
    "»": "ङ्क",
    "¼": "ङ्ग",
    "Œ": "ङ्ख",
    "½": "च्च",
    "¾": "ज्ज",
    "Â": "ञ्च",
    "Ã": "ञ्ज",
    "Ä": "त्त",
    "õ": "स्न",
    "Ï": "द्ध",
    "Ñ": "द्भ",
    "Ì": "द्ग",
    "Ö": "द्व",
    "*": "द्य",
    "Ú": "न्न",
    "Ý": "प्त",
    "_": "भ्",
    "ç": "म्न",
    "í": "श्च",
    "ï": "श्र",
    "ñ": "श्व",
    "ò": "ष्ट",
    "ó": "ष्ठ",
    "ù": "हृ",
    "Ê": "दु",
    "ü": "ह्म",
    "ý": "ह्य",
    "÷": "हु",
    "†": "दृ",
    "é": "रु",
    "ê": "रू",
    # added in 1.1.0 (SrimadBhagawadGeeta_Sanskrit.pdf); example word in comments
    "$": "ई",  # ईक्षते
    "\\": "ऋ",  # ऋषयः
    "^": "ऊ",  # ऊर्ध्वं
    "ª": "ू",  # कूटस्थ (ū under क)
    "ƒ": "ू",  # भगवद्रूपं (ū under द्र)
    "¯": "ृ",  # मोहाद्गृहीत्वा, नाहङ्कृतो (ṛ under a ligature)
    "~": "ँ",  # शुभाँल्लोकान्
    "(": "्य",  # बुद्ध्या (ya-phala)
    ")": "फ",  # फलेषु
    "H": "झ",  # झषाणां
    "Q": "ठ",  # पठेत्
    "G": "ग्",
    "L": "ल्",
    "W": "थ्",
    "Y": "य्",
    "¸": "घ्",
    "Á": "ञ्",  # half forms
    "¢": "ग्र",  # ग्रथितां
    "Í": "द्ग्र",  # असद्ग्राहान्
    "º": "घ्र",  # घ्राण
    "¿": "ज्र",  # वज्रं
    "À": "छ्र",  # यच्छ्रेयः
    "È": "त्र्",  # रात्र्यागमे
    "Ø": "ध्र",  # ध्रुवो
    "è": "म्र",  # म्रियते
    "ì": "व्र",  # व्रजेत्
    "ÿ": "ह्र",  # ह्रियते
    "Ü": "न्र",  # वसून्रुद्रान्
    "Ù": "न्त्र",  # मन्त्रो
    "±": "क्त्र",  # वक्त्र
    "¬": "क्ल",  # क्लैब्यं
    "Š": "क्क",  # यतवाक्काय
    "“": "ङ्क्त",  # भुङ्क्ते
    "Å": "त्त्",  # तत्त्व
    "Æ": "त्न",  # सपत्नम्
    "Î": "द्द",  # अश्रद्दधान
    "Ò": "द्म",  # पद्म
    "Ó": "द्ब",  # तद्बुद्धयः
    "™": "द्व्य",  # मद्व्यपाश्रयः
    "×": "ध्न",  # निबध्नन्ति
    "Û": "न्न्",  # सन्न्यास (printed with double न)
    "Þ": "प्त्",  # अलोलुप्त्वं
    "ß": "प्न",  # आप्नोति
    "î": "श्न",  # अश्नुते
    "ð": "श्ल",  # श्लोकाः
    "‘": "ल्ल",  # फुल्लारविन्दा
    "’": "ह्ल",  # प्रह्लाद
    "ø": "हू",  # बहून्
    "Ë": "दू",  # दूरेण
    "û": "ह्न",  # वह्निः
    "þ": "ह्व",  # जुह्वति
    "Ÿ": "ह्ण",  # गृह्णाति
    # layout
    " ": " ",
    "-": "-",
}

_TOKEN = re.compile("|".join(re.escape(k) for k in sorted(TABLE, key=len, reverse=True)) + "|.", re.S)

_CONSONANT = "[क-हक़-य़]"
_CLUSTER = f"(?:{_CONSONANT}{_VIRAMA})*{_CONSONANT}"
# short-i placeholder followed by a consonant cluster → cluster + ि
_I_REORDER = re.compile(f"{_I_MARK}({_CLUSTER})")
# a syllable (cluster + optional vowel signs) followed by reph placeholder → र् + syllable
_SIGNS = "[ा-ौॢॣ]*"
_REPH_REORDER = re.compile(f"({_CLUSTER}{_SIGNS}[ंँ]?){_REPH}")  # reph may follow ं (मेघवर्णं)


def decode(raw: str) -> tuple[str, list[str]]:
    """Return (unicode_text, unknown_codes). Unknown codes are kept in the output unchanged."""
    out: list[str] = []
    unknown: list[str] = []
    for tok in _TOKEN.findall(raw):
        mapped = TABLE.get(tok)
        if mapped is None:
            unknown.append(tok)
            out.append(tok)
        else:
            out.append(mapped)
    text = "".join(out)
    text = _I_REORDER.sub(lambda m: m.group(1) + "ि", text)
    text = _REPH_REORDER.sub(lambda m: "र" + _VIRAMA + m.group(1), text)
    # placeholders that could not be placed are a decoding failure, keep them visible
    for mark, name in ((_I_MARK, "i"), (_REPH, "R")):
        if mark in text:
            unknown.append(f"unplaced:{name}")
    return unicodedata.normalize("NFC", text), unknown
