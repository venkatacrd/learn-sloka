"""Split lines into units: verse / heading / speaker / other (FR-EX-09, 10, 11)."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from sanskrit_extract.config import Profile
from sanskrit_extract.models import Line, PageResult
from sanskrit_extract.syllables import script_of

_DEVA_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


@dataclass
class Unit:
    unit_type: str
    lines: list[Line]  # lines carry normalized `text`
    verse_ref: dict[str, str] | None = None
    flags: list[str] = field(default_factory=list)


def normalize_ref(label: str) -> str:
    digits = label.translate(_DEVA_DIGITS)
    return ".".join(re.findall(r"\d+", digits))


@dataclass(frozen=True)
class _Ctx:
    width: float
    body_size: float


def _body_size(pages: list[PageResult]) -> float:
    sizes = Counter(round(ln.size) for p in pages for ln in p.lines if ln.size > 0)
    return float(sizes.most_common(1)[0][0]) if sizes else 0.0


class Segmenter:
    def __init__(self, profile: Profile) -> None:
        self.p = profile
        self.verse_end = re.compile(profile.verse_end)
        self.speaker = re.compile(profile.speaker)
        self.colophon_start = re.compile(profile.colophon_start)
        self.colophon_end = re.compile(profile.colophon_end)
        self.toc_entry = re.compile(profile.toc_entry)

    def _is_title(self, text: str) -> bool:
        words = [w for w in text.replace("-", " ").split() if not set(w) <= set("।॥")]
        return "।" not in text and "॥" not in text and 0 < len(words) <= self.p.title_max_words

    def _is_heading(self, ln: Line, ctx: _Ctx) -> bool:
        if "।" in ln.text:
            return False
        x0, _, x1, _ = ln.bbox
        centred = abs((x0 + x1) / 2 - ctx.width / 2) <= self.p.centered_tolerance * ctx.width
        narrow = (x1 - x0) <= self.p.heading_max_width * ctx.width
        other_size = ln.size > 0 and ctx.body_size > 0 and abs(round(ln.size) - ctx.body_size) >= 1
        return narrow and (centred or other_size)

    def segment(self, pages: list[PageResult]) -> list[Unit]:
        body = _body_size(pages)
        ctx_by_page = {p.number: _Ctx(p.width, body) for p in pages}
        units: list[Unit] = []
        pending: list[Line] = []
        held: list[Line] = []  # speaker lines found inside an open verse
        block_start = 0  # index in `pending` where the current block starts
        prev: Line | None = None  # previous line on the same page (speaker lines included)

        colophon: list[Line] | None = None  # an open multi-line colophon

        def flush_incomplete() -> None:
            nonlocal pending, held, block_start
            if len(pending) == 1 and self._is_title(pending[0].text):
                units.append(Unit("heading", pending))
            elif pending:
                units.append(Unit("other", pending, flags=["needs_review"]))
            units.extend(Unit("speaker", [s]) for s in held)
            pending, held, block_start = [], [], 0

        for page in pages:
            ctx = ctx_by_page[page.number]
            prev = None
            for ln in page.lines:
                text = ln.text
                gap_before = prev is not None and ln.bbox[1] - prev.bbox[3] > self.p.block_gap_factor * (
                    prev.bbox[3] - prev.bbox[1]
                )
                prev = ln
                if colophon is not None:
                    colophon.append(ln)
                    if text.rstrip().endswith("॥"):
                        cm = self.verse_end.search(text)
                        if cm and (cm.group("num") or cm.group("ascii")):  # it was a verse after all
                            label = cm.group(0).strip()
                            cref = {"label": label, "normalized": normalize_ref(label)}
                            units.append(Unit("verse", colophon, verse_ref=cref))
                        else:
                            units.append(Unit("heading", colophon))
                        colophon = None
                    continue
                if self.speaker.search(text):
                    if pending:
                        held.append(ln)
                    else:
                        units.append(Unit("speaker", [ln]))
                    continue
                if script_of(text) == "latin":  # e.g. an English footnote: never part of a verse (P2-02)
                    flush_incomplete()
                    units.append(Unit("other", [ln], flags=["needs_review"]))
                    continue
                m = self.verse_end.search(text)
                numbered = bool(m and (m.group("num") or m.group("ascii")))
                colophon_like = self.colophon_start.search(text) or self.colophon_end.search(text)
                if not numbered and "।" not in text and colophon_like:
                    flush_incomplete()
                    if text.rstrip().endswith("॥") or self.colophon_end.search(text):
                        units.append(Unit("heading", [ln]))
                    else:
                        colophon = [ln]
                    continue
                if self.toc_entry.search(text):
                    flush_incomplete()
                    units.append(Unit("heading", [ln]))
                    continue
                closes_open_verse = bool(m) and bool(pending)
                if not numbered and not closes_open_verse and self._is_heading(ln, ctx):
                    flush_incomplete()
                    units.append(Unit("heading", [ln]))
                    continue
                if pending and gap_before:
                    block_start = len(pending)
                pending.append(ln)
                if m:
                    if block_start:  # text before a gap is not part of this verse
                        before = pending[:block_start]
                        if len(before) == 1 and self._is_title(before[0].text):
                            units.append(Unit("heading", before))
                        else:
                            units.append(Unit("other", before, flags=["needs_review"]))
                        pending = pending[block_start:]
                    flags: list[str] = []
                    ref = None
                    if numbered:
                        label = m.group(0).strip()
                        ref = {"label": label, "normalized": normalize_ref(label)}
                    else:
                        flags.append("unnumbered_verse")
                    if held:
                        flags.append("split_by_speaker")
                    if len({x.page for x in pending}) > 1:
                        flags.append("crosses_page")
                    units.append(Unit("verse", pending, verse_ref=ref, flags=flags))
                    units.extend(Unit("speaker", [s]) for s in held)
                    pending, held, block_start = [], [], 0
        flush_incomplete()
        if colophon is not None:
            units.append(Unit("heading", colophon, flags=["needs_review"]))  # never closed by `॥`
        return units
