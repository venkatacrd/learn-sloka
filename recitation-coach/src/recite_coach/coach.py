"""The check pipeline used by both the CLI and the page: audio -> transcript -> comparison -> feedback JSON."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .compare import Comparison, compare
from .feedback import to_json
from .library import Sloka, load_chapter
from .model import Pcm, Recognizer, load_audio


class UnknownSloka(KeyError):
    """Sloka not in the chapter, or without text/audio."""


@dataclass
class Coach:
    slokas: dict[int, Sloka]
    recognizer: Recognizer
    _teacher: dict[int, Comparison] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    @classmethod
    def open(cls, text_jsonl: Path, audio_dir: Path | None) -> Coach:
        return cls(load_chapter(text_jsonl, audio_dir), Recognizer.load())

    def sloka(self, n: int) -> Sloka:
        s = self.slokas.get(n)
        if s is None or not s.lines:
            raise UnknownSloka(n)
        return s

    def teacher(self, n: int) -> Comparison | None:
        """The instructor's recording compared with the text: gives each word's time in the instructor audio."""
        s = self.sloka(n)
        if s.audio is None:
            return None
        with self._lock:
            if n not in self._teacher:
                try:
                    self._teacher[n] = compare(s.lines, self.recognizer.transcribe(load_audio(s.audio)))
                except Exception:  # unreadable instructor file: feedback still works, only word playback is lost
                    return None
            return self._teacher[n]

    def check(self, n: int, pcm: Pcm) -> dict[str, Any]:
        s = self.sloka(n)
        with self._lock:
            heard = self.recognizer.transcribe(pcm)
        result = compare(s.lines, heard)
        out = to_json(result, n, self.teacher(n))
        out["duration_s"] = round(len(pcm) / 16000, 2)
        return out

    def sloka_json(self, n: int) -> dict[str, Any]:
        s = self.sloka(n)
        return {
            "number": n,
            "available": s.available,
            "lines": [{"speaker": ln.speaker, "dev": ln.dev, "iast": ln.iast} for ln in s.lines],
        }
