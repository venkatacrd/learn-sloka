"""Legacy (pre-Unicode) font mapping tables (FR-EX-05). Registry keyed by lower-case font name."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from sanskrit_extract.legacy_fonts import sanskrit99


@dataclass(frozen=True)
class FontMap:
    name: str
    version: str
    decode: Callable[[str], tuple[str, list[str]]]


REGISTRY: dict[str, FontMap] = {
    "sanskrit99": FontMap(sanskrit99.NAME, sanskrit99.VERSION, sanskrit99.decode),
}


def get(font: str) -> FontMap | None:
    return REGISTRY.get(font.lower())
