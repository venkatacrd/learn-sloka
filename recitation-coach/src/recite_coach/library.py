"""Sloka library: text from the converter's .romanized.jsonl, instructor audio from the splitter (FR-RC-01)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_PUNCT = re.compile(r"[।॥|0-9०-९]+")
_NUM = re.compile(r"(\d+)\D*$")


@dataclass(frozen=True)
class Word:
    dev: str
    iast: str

    @property
    def telugu(self) -> str:
        """Telugu script, converted from the Devanagari letter for letter (FR-RC-03)."""
        from indic_transliteration import sanscript

        return str(sanscript.transliterate(self.dev, sanscript.DEVANAGARI, sanscript.TELUGU))


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

    @property
    def telugu(self) -> str:
        return " ".join(w.telugu for w in self.words)


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


def _records(text_jsonl: Path) -> list[dict[str, Any]]:
    return [json.loads(row) for row in text_jsonl.read_text(encoding="utf-8").splitlines() if row.strip()]


def _verse_number(rec: dict[str, Any]) -> int | None:
    ex = rec["extracted"]
    m = _NUM.search(str((ex.get("verse_ref") or {}).get("normalized") or ""))
    return int(m.group(1)) if ex["unit_type"] == "verse" and m else None


def _slokas(records: list[dict[str, Any]]) -> dict[int, Sloka]:
    """Verse number -> Sloka. A speaker line goes before the next verse, or between the halves of a
    `split_by_speaker` verse that it follows."""
    slokas: dict[int, Sloka] = {}
    pending: list[Line] = []
    last: Sloka | None = None
    last_split = False
    for rec in records:
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
        n = _verse_number(rec)
        if n is None:
            pending, last, last_split = [], None, False
            continue
        verse = [p for d, i in zip(dev_lines, iast_lines, strict=True) for p in _padas(_line(d, i))]
        sloka = Sloka(n, _number_padas(pending + verse))
        slokas[n] = sloka
        pending, last = [], sloka
        last_split = "split_by_speaker" in ex["quality"]["flags"]
    return dict(sorted(slokas.items()))


def _attach_audio(slokas: dict[int, Sloka], audio_dir: Path) -> int:
    """Link `<name>_sloka_NN.mp3` files to slokas; returns how many sloka files the folder holds."""
    files = sorted(audio_dir.glob("*_sloka_*.mp3"))
    for mp3 in files:
        m = _NUM.search(mp3.stem)
        if m and int(m.group(1)) in slokas and slokas[int(m.group(1))].audio is None:
            slokas[int(m.group(1))].audio = mp3
    return len(files)


def load_chapter(text_jsonl: Path, audio_dir: Path | None) -> dict[int, Sloka]:
    """One chapter's text (all of the file) and its instructor folder."""
    slokas = _slokas(_records(text_jsonl))
    if audio_dir is not None and audio_dir.is_dir():
        _attach_audio(slokas, audio_dir)
    return slokas


# --- whole book (FR-RC-14) ---------------------------------------------------------------------------------

ORDINALS = [  # chapter 1 … 18 in "॥ अथ <ordinal>ोऽध्यायः ॥"
    "प्रथम", "द्वितीय", "तृतीय", "चतुर्थ", "पञ्चम", "षष्ठ", "सप्तम", "अष्टम", "नवम",
    "दशम", "एकादश", "द्वादश", "त्रयोदश", "चतुर्दश", "पञ्चदश", "षोडश", "सप्तदश", "अष्टादश",
]  # fmt: skip
_CHAPTER_HEADING = re.compile(r"अथ\s+(\S+?)ोऽध्यायः")
_CHAPTER_DIR = re.compile(r"ch\D{0,3}?0*(\d+)", re.IGNORECASE)


@dataclass
class Chapter:
    number: int
    slokas: dict[int, Sloka]
    title_dev: str = ""
    title_iast: str = ""
    audio_parts: int = 0  # instructor sloka files found for this chapter

    @property
    def audio_matches(self) -> bool:
        """The splitter found as many slokas as the book has: sloka N's audio is verse N."""
        return self.audio_parts == len(self.slokas)


def _parts(records: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Split where the verse number restarts; headings/speakers before a verse 1 belong to its part."""
    parts: list[list[dict[str, Any]]] = []
    lead: list[dict[str, Any]] = []
    last = 0
    for rec in records:
        n = _verse_number(rec)
        if n is None:
            lead.append(rec)
            continue
        if not parts or n < last:
            parts.append([])
        parts[-1].extend([*lead, rec])
        lead, last = [], n
    if parts:
        parts[-1].extend(lead)
    return parts


def _chapter_heading(part: list[dict[str, Any]]) -> tuple[int | None, str, str]:
    """(chapter number from `अथ <ordinal>ोऽध्यायः`, title Devanagari, title IAST) from the part's opening headings."""
    number, title_dev, title_iast = None, "", ""
    for rec in part:
        ex = rec["extracted"]
        if _verse_number(rec) is not None:
            break
        if ex["unit_type"] != "heading":
            continue
        text = " ".join(ex["lines"]).strip()
        m = _CHAPTER_HEADING.search(text)
        if m and m.group(1) in ORDINALS:
            number = ORDINALS.index(m.group(1)) + 1
        elif number is not None and not title_dev and text.rstrip("॥ ").endswith("योगः"):
            title_dev = text.strip(" ॥")
            title_iast = " ".join(rec["romanized_lines"]["iast"]).strip(" |")
    return number, title_dev, title_iast


def _audio_folders(audio: Path) -> list[tuple[int | None, Path]]:
    """(chapter number or None, folder) for a sloka folder, or for each per-chapter folder under a root."""

    def number(folder: Path) -> int | None:
        m = _CHAPTER_DIR.search(folder.name) or next(
            (m for f in folder.glob("*_sloka_*.mp3") if (m := _CHAPTER_DIR.search(f.stem))), None
        )
        return int(m.group(1)) if m else None

    if any(audio.glob("*_sloka_*.mp3")):
        return [(number(audio), audio)]
    return [(number(d), d) for d in sorted(audio.iterdir()) if d.is_dir() and any(d.glob("*_sloka_*.mp3"))]


def load_book(text_jsonl: Path, audio: Path | None) -> dict[int, Chapter]:
    """Chapter number -> Chapter, from a chapter's or a whole book's text and the instructor audio (FR-RC-14)."""
    parts = _parts(_records(text_jsonl))
    heads = [_chapter_heading(p) for p in parts]
    chapters: dict[int, Chapter] = {}
    if any(h[0] is not None for h in heads):
        for part, (num, tdev, tiast) in zip(parts, heads, strict=True):
            if num is not None and num not in chapters:  # parts without a chapter heading: not a chapter
                chapters[num] = Chapter(num, _slokas(part), tdev, tiast)
    else:
        for k, part in enumerate(parts, 1):
            chapters[k] = Chapter(k, _slokas(part))
    if audio is not None and audio.is_dir():
        folders = _audio_folders(audio)
        for num, folder in folders:
            target = chapters.get(num) if num is not None else None
            if target is None and len(chapters) == 1 and len(folders) == 1:  # single chapter, unnamed folder
                target = next(iter(chapters.values()))
            if target is not None and not target.audio_parts:
                target.audio_parts = _attach_audio(target.slokas, folder)
    return dict(sorted(chapters.items()))
