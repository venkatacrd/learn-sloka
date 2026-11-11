"""Transliteration engine interface (FR-TR-10)."""

from __future__ import annotations

from typing import Protocol


class TransliterationEngine(Protocol):
    name: str

    def version(self) -> str: ...

    def from_devanagari(self, text: str, scheme: str) -> str: ...

    def to_devanagari(self, text: str, scheme: str) -> str: ...
