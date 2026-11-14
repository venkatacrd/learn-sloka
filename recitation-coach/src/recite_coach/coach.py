"""The check pipeline used by both the CLI and the page: audio -> transcript -> comparison -> feedback JSON."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .compare import Comparison, compare
from .feedback import to_json
from .library import Chapter, Sloka, load_book
from .model import Pcm, Recognizer, load_audio


class UnknownSloka(KeyError):
    """Chapter or sloka not in the text."""


@dataclass
class Coach:
    chapters: dict[int, Chapter]
    recognizer: Recognizer
    _teacher: dict[tuple[int, int], Comparison] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    @classmethod
    def open(cls, text_jsonl: Path, audio: Path | None) -> Coach:
        return cls(load_book(text_jsonl, audio), Recognizer.load())

    @property
    def only_chapter(self) -> int | None:
        return next(iter(self.chapters)) if len(self.chapters) == 1 else None

    def chapter(self, c: int) -> Chapter:
        ch = self.chapters.get(c)
        if ch is None:
            raise UnknownSloka((c, 0))
        return ch

    def sloka(self, c: int, n: int) -> Sloka:
        s = self.chapter(c).slokas.get(n)
        if s is None or not s.lines:
            raise UnknownSloka((c, n))
        return s

    def teacher(self, c: int, n: int) -> Comparison | None:
        """The instructor's recording compared with the text: gives each word's time in the instructor audio."""
        s = self.sloka(c, n)
        if s.audio is None:
            return None
        with self._lock:
            if (c, n) not in self._teacher:
                try:
                    self._teacher[(c, n)] = compare(s.lines, self.recognizer.transcribe(load_audio(s.audio)))
                except Exception:  # unreadable instructor file: feedback still works, only word playback is lost
                    return None
            return self._teacher[(c, n)]

    def check(self, c: int, n: int, pcm: Pcm) -> dict[str, Any]:
        s = self.sloka(c, n)
        with self._lock:
            heard = self.recognizer.transcribe(pcm)
        out: dict[str, Any] = {"chapter": c}
        out.update(to_json(compare(s.lines, heard), n, self.teacher(c, n)))
        out["duration_s"] = round(len(pcm) / 16000, 2)
        return out

    def audio_warning(self, c: int) -> str:
        ch = self.chapter(c)
        if not ch.audio_parts or ch.audio_matches:
            return ""
        return (
            f"The instructor recording of this chapter was split into {ch.audio_parts} parts, but the book has "
            f"{len(ch.slokas)} slokas, so this audio may be a different sloka. Check the chapter's review page "
            "and re-split it before relying on it."
        )

    def chapters_json(self) -> list[dict[str, Any]]:
        return [
            {
                "number": ch.number,
                "title_dev": ch.title_dev,
                "title_iast": ch.title_iast,
                "audio_parts": ch.audio_parts,
                "audio_matches": ch.audio_matches,
                "slokas": [{"number": n, "available": s.available} for n, s in ch.slokas.items()],
            }
            for ch in self.chapters.values()
        ]

    def sloka_json(self, c: int, n: int) -> dict[str, Any]:
        s, ch = self.sloka(c, n), self.chapter(c)
        return {
            "chapter": c,
            "number": n,
            "title_iast": ch.title_iast,
            "available": s.available,
            "audio_warning": self.audio_warning(c),
            "lines": [{"speaker": ln.speaker, "dev": ln.dev, "telugu": ln.telugu, "iast": ln.iast} for ln in s.lines],
        }
