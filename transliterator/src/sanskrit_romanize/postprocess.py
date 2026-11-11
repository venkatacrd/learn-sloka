"""Conventions applied around the engine (FR-TR-03..05), and their exact reverse for the round-trip check."""

from __future__ import annotations

import re
import unicodedata

from sanskrit_romanize.config import Config

HIATUS = ""  # marks इ/उ that follow a short a (would otherwise read as ai/au)
_CONS = "[क-हक़-य़]़?"
_HIATUS_DEV = re.compile(f"({_CONS}|अ)(?=[इउ])")
_DEVA_DIGITS = "०१२३४५६७८९"
_TO_ASCII = str.maketrans(_DEVA_DIGITS, "0123456789")
_TO_DEVA = str.maketrans("0123456789", _DEVA_DIGITS)
_DANDA_OUT = {"pipe": ("|", "||"), "devanagari": ("।", "॥"), "period": (".", "..")}


def mark_hiatus(dev: str) -> str:
    return _HIATUS_DEV.sub(lambda m: m.group(1) + HIATUS, dev)


def after_engine(text: str, scheme: str, cfg: Config) -> str:
    """Engine output → our conventions for this scheme."""
    if scheme == "iast":
        text = text.replace(HIATUS + "i", "ï").replace(HIATUS + "u", "ü").replace("~", "m̐")
    elif scheme == "iso15919":
        text = text.replace(HIATUS, ":")
    text = text.replace(HIATUS, "")
    if scheme in ("iast", "iso15919"):
        single, double = _DANDA_OUT[cfg.danda_style]
        text = text.replace("||", "\u0000").replace("|", single).replace("\u0000", double)
    text = text.translate(_TO_ASCII if cfg.digits == "ascii" else _TO_DEVA)
    return unicodedata.normalize("NFC", text)


def before_reverse(iast: str, cfg: Config) -> str:
    """Undo `after_engine` for IAST so the engine can convert back to Devanagari."""
    text = unicodedata.normalize("NFC", iast)
    text = text.replace("ï", HIATUS + "i").replace("ü", HIATUS + "u").replace("m̐", "~")
    single, double = _DANDA_OUT[cfg.danda_style]
    if cfg.danda_style != "pipe":
        text = text.replace(double, "\u0000").replace(single, "|").replace("\u0000", "||")
    return text


def ascii_fold(iast: str) -> str:
    """FR-TR-03: lossy search form."""
    text = unicodedata.normalize("NFD", iast.replace("m̐", "m"))
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    text = re.sub(r"[|।॥]+|\.{2,}", " ", text)
    return re.sub(r"\s+", " ", text).strip()
