"""Sloka library: text from the converter's .romanized.jsonl, instructor audio from the splitter (FR-RC-01)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

_PUNCT = re.compile(r"[।॥|0-9०-९]+")
_NUM = re.compile(r"(\d+)\D*$")


@dataclass(frozen=True)
class Word:
    dev: str
    iast: str


@dataclass(frozen=True)
class Line:
    words: tuple[Word, ...]
    speaker: bool = False  # "… उवाच" line: may or may not be spoken in the recording
    pada: int = 0  # 1-4 for the recited lines (pādas) of the sloka, 0 for a speaker line

    @property
    def dev(self) -> str:
        return " ".join(w.dev for w in self.words)

    @property
    def iast(self) -> str:
        return " ".join(w.iast for w in self.words)


@dataclass
class Sloka:
    number: int
    lines: list[Line] = field(default_factory=list)
    audio: Path | None = None

    @property
    def available(self) -> bool:
        return self.audio is not None and bool(self.lines)


def _words(dev: str, iast: str) -> tuple[Word, ...]:
    d = _PUNCT.sub(" ", dev).replace("-", " ").split()
    i = _PUNCT.sub(" ", iast).replace("-", " ").split()
    if len(i) != len(d):
        from indic_transliteration import sanscript

        i = [sanscript.transliterate(w, sanscript.DEVANAGARI, sanscript.IAST) for w in d]
    return tuple(Word(a, b) for a, b in zip(d, i, strict=True))


def _line(dev: str, iast: str, speaker: bool = False) -> Line:
    return Line(_words(dev, iast), speaker)


_CONS = set("कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसहळ")
_VOWELS = set("अआइईउऊऋॠऌएऐओऔ")


def syllables(dev: str) -> int:
    """Vowels in a Devanagari word: independent vowels + consonants not followed by a virama."""
    n = 0
    for i, c in enumerate(dev):
        if c in _VOWELS or (c in _CONS and (i + 1 == len(dev) or dev[i + 1] != "्")):
            n += 1
    return n


def _padas(line: Line) -> list[Line]:
    """A printed half-verse holds two recited lines (pādas): split at the word boundary nearest half the syllables."""
    words = line.words
    if len(words) < 2:
        return [line]
    counts = [syllables(w.dev) for w in words]
    total, best, run = sum(counts), 1, 0
    for k in range(1, len(words)):
        run += counts[k - 1]
        if abs(run - total / 2) < abs(sum(counts[:best]) - total / 2):
            best = k
    return [Line(words[:best]), Line(words[best:])]


def _number_padas(lines: list[Line]) -> list[Line]:
    out, n = [], 0
    for ln in lines:
        if ln.speaker:
            out.append(ln)
        else:
            n += 1
            out.append(Line(ln.words, False, n))
    return out


def load_chapter(text_jsonl: Path, audio_dir: Path | None) -> dict[int, Sloka]:
    """Verse number -> Sloka. A speaker line goes before the next verse, or between the halves of a
    `split_by_speaker` verse that it follows."""
    slokas: dict[int, Sloka] = {}
    pending: list[Line] = []
    last: Sloka | None = None
    last_split = False
    for row in text_jsonl.read_text(encoding="utf-8").splitlines():
        if not row.strip():
            continue
        rec = json.loads(row)
        ex = rec["extracted"]
        dev_lines, iast_lines = ex["lines"], rec["romanized_lines"]["iast"]
        if ex["unit_type"] == "speaker":
            spk = [_line(d, i, speaker=True) for d, i in zip(dev_lines, iast_lines, strict=True)]
            if last is not None and last_split:
                k = next(i for i, ln in enumerate(last.lines) if ln.pada == 2) + 1  # after the first half-verse
                last.lines[k:k] = spk  # spoken between the verse's halves
                last.lines = _number_padas(last.lines)
                last_split = False
            else:
                pending = spk
            continue
        ref = (ex.get("verse_ref") or {}).get("normalized")
        m = _NUM.search(str(ref or ""))
        if ex["unit_type"] != "verse" or not m:
            pending, last, last_split = [], None, False
            continue
        n = int(m.group(1))
        verse = [p for d, i in zip(dev_lines, iast_lines, strict=True) for p in _padas(_line(d, i))]
        sloka = Sloka(n, _number_padas(pending + verse))
        slokas[n] = sloka
        pending, last = [], sloka
        last_split = "split_by_speaker" in ex["quality"]["flags"]
    if audio_dir is not None and audio_dir.is_dir():
        for mp3 in sorted(audio_dir.glob("*_sloka_*.mp3")):
            m = _NUM.search(mp3.stem)
            if m and int(m.group(1)) in slokas and slokas[int(m.group(1))].audio is None:
                slokas[int(m.group(1))].audio = mp3
    return dict(sorted(slokas.items()))
