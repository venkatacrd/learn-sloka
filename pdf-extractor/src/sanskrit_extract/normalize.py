"""text_raw → text cleanup rules (FR-EX-07). Each rule is deterministic and can be switched off."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable

from pydantic import BaseModel

_DEVA = "ऀ-ॿ"


class NormalizeConfig(BaseModel):
    nfc: bool = True
    remove_soft_hyphen_and_controls: bool = True
    danda_lookalikes: bool = True
    zero_width_joiners: bool = True
    danda_spacing: bool = True
    collapse_spaces: bool = True


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def remove_soft_hyphen_and_controls(s: str) -> str:
    """Drop soft hyphens and control/format characters (newlines and ZWJ/ZWNJ are kept)."""
    out = []
    for ch in s:
        if ch in "\n\u200c\u200d":
            out.append(ch)
        elif ch == "\u00ad" or unicodedata.category(ch) in ("Cc", "Cf"):
            continue
        else:
            out.append(ch)
    return "".join(out)


_DOUBLE_LOOKALIKE = re.compile(f"(?<=[{_DEVA}\u200c\u200d])([ \\t]*)(?:\\|\\||II)")
_SINGLE_LOOKALIKE = re.compile(f"(?<=[{_DEVA}\u200c\u200d])([ \\t]*)(?:\\||I(?=\\s|$))")


def danda_lookalikes(s: str) -> str:
    """`||`/`II` → `॥` and `|`/`I` → `।`, only right after Devanagari (incl. Devanagari digits)."""
    s = _DOUBLE_LOOKALIKE.sub(lambda m: m.group(1) + "॥", s)
    return _SINGLE_LOOKALIKE.sub(lambda m: m.group(1) + "।", s)


_ZW = re.compile("(?<!्)[‌‍]")


def zero_width_joiners(s: str) -> str:
    """Drop ZWJ/ZWNJ except right after a virama, where they change the conjunct's shape."""
    return _ZW.sub("", s)


_NUM = "[०-९0-9]+(?:[.\\-–][०-९0-9]+)*"
_VERSE_NUM = re.compile(f"॥\\s*({_NUM})\\s*॥")
_BEFORE_DANDA = re.compile("[ \\t]*([।॥])")


def danda_spacing(s: str) -> str:
    """One space before `।`/`॥`; verse numbers as `॥ १ ॥`. Spacing only."""
    s = _VERSE_NUM.sub(lambda m: f"॥ {m.group(1)} ॥", s)
    s = _BEFORE_DANDA.sub(r" \1", s)
    return "\n".join(line.strip() for line in s.split("\n"))


_SPACES = re.compile(r"[ \t  -  　]+")


def collapse_spaces(s: str) -> str:
    return "\n".join(_SPACES.sub(" ", line).strip() for line in s.split("\n"))


RULES: tuple[tuple[str, Callable[[str], str]], ...] = (
    ("nfc", nfc),
    ("remove_soft_hyphen_and_controls", remove_soft_hyphen_and_controls),
    ("zero_width_joiners", zero_width_joiners),  # before dandas, so a joiner never hides a `|`
    ("danda_lookalikes", danda_lookalikes),
    ("danda_spacing", danda_spacing),
    ("collapse_spaces", collapse_spaces),
)


def normalize(s: str, config: NormalizeConfig | None = None) -> str:
    cfg = config or NormalizeConfig()
    for name, rule in RULES:
        if getattr(cfg, name):
            s = rule(s)
    return nfc(s) if cfg.nfc else s
