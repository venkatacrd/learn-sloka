"""Find sloka boundaries in a chanted recitation (FR-AS-02..05).

A segment is a stretch of voice between pauses (one pāda = one line). Every half-verse (2 lines) contains
exactly one line that ends on a falling pitch (a *cadence*). Whether the half-verse ends *on* that line or on
the *next* one depends on the reciter; it is decided from the pauses (the pause after a half-verse is longer)
or set explicitly. A sloka is `half_verses_per_sloka` half-verses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import numpy.typing as npt

Pcm = npt.NDArray[np.float32]
PartKind = Literal["intro", "sloka", "closing"]

NO_CADENCE_PATTERN = "no_cadence_pattern"
INCOMPLETE_LAST_SLOKA = "incomplete_last_sloka"
HALF_VERSE_END_UNCERTAIN = "half_verse_end_uncertain"
HalfVerseEnd = Literal["auto", "cadence", "next"]


@dataclass(frozen=True)
class Settings:
    silence_drop_db: float = 20.0
    min_gap_s: float = 0.3
    min_segment_s: float = 0.3
    tail_s: float = 0.4
    fmin_hz: float = 70.0
    fmax_hz: float = 400.0
    min_cadence_separation_st: float = 2.0
    half_verses_per_sloka: int = 2
    half_verse_end: HalfVerseEnd = "auto"  # cadence line ends the half-verse, or the line after it
    min_half_verse_vote: float = 0.6  # auto: share of cadences whose pauses must agree
    min_vote_diff_s: float = 0.03  # auto: pauses closer than this are a tie and do not vote
    breath_gap_ratio: float = 0.75  # pause < ratio × typical pause inside a half-verse = breath inside a line


@dataclass(frozen=True)
class Segment:
    start_s: float
    end_s: float
    tail_pitch_st: float | None  # semitones relative to 100 Hz; None if unvoiced
    cadence: bool = False


@dataclass(frozen=True)
class Part:
    kind: PartKind
    number: int  # sloka number; 0 for intro/closing
    start_s: float
    end_s: float
    segments: int
    cadences: int


@dataclass
class Analysis:
    duration_s: float
    silence_db: float
    cadence_threshold_st: float | None
    cadence_separation_st: float | None
    segments: list[Segment]
    parts: list[Part]
    half_verse_end: str | None = None  # resolved "cadence" / "next"
    half_verse_vote: float | None = None  # auto: share of cadences agreeing with the choice
    warnings: list[str] = field(default_factory=list)

    @property
    def slokas(self) -> list[Part]:
        return [p for p in self.parts if p.kind == "sloka"]


def _frame_db(pcm: Pcm, hop: int) -> npt.NDArray[np.float64]:
    n = len(pcm) // hop
    frames = pcm[: n * hop].astype(np.float64).reshape(n, hop)
    return 20.0 * np.log10(np.sqrt((frames**2).mean(axis=1)) + 1e-9)


def silence_threshold_db(pcm: Pcm, sample_rate: int, settings: Settings = Settings()) -> float:
    db = _frame_db(pcm, sample_rate // 100)
    active = db[db > -70.0]
    if active.size == 0:
        return 0.0
    return float(np.median(active)) - settings.silence_drop_db


def find_segments(pcm: Pcm, sample_rate: int, settings: Settings = Settings()) -> list[tuple[float, float]]:
    """Voice stretches (start, end) in seconds; short pauses bridged, clicks dropped (FR-AS-02)."""
    hop = sample_rate // 100
    db = _frame_db(pcm, hop)
    loud = db >= silence_threshold_db(pcm, sample_rate, settings)
    runs: list[list[int]] = []
    i, n = 0, len(loud)
    while i < n:
        if loud[i]:
            j = i
            while j < n and loud[j]:
                j += 1
            if runs and (i - runs[-1][1]) / 100 < settings.min_gap_s:
                runs[-1][1] = j
            else:
                runs.append([i, j])
            i = j
        else:
            i += 1
    return [(a / 100, b / 100) for a, b in runs if (b - a) / 100 >= settings.min_segment_s]


def tail_pitch_st(
    pcm: Pcm, sample_rate: int, start_s: float, end_s: float, settings: Settings = Settings()
) -> float | None:
    """Median pitch (semitones re 100 Hz) of the last `tail_s` of a segment, by autocorrelation."""
    a = int(max(start_s, end_s - settings.tail_s) * sample_rate)
    seg = pcm[a : int(end_s * sample_rate)].astype(np.float64)
    win, hop = int(0.04 * sample_rate), int(0.01 * sample_rate)
    if len(seg) < win:
        return None
    frames = np.lib.stride_tricks.sliding_window_view(seg, win)[::hop]
    frames = frames - frames.mean(axis=1, keepdims=True)
    spec = np.fft.rfft(frames, n=2 * win, axis=1)
    ac = np.fft.irfft(np.abs(spec) ** 2, axis=1)[:, :win]
    lo = int(sample_rate / settings.fmax_hz)
    hi = min(win - 1, int(sample_rate / settings.fmin_hz))
    lag = lo + np.argmax(ac[:, lo:hi], axis=1)
    peak = ac[np.arange(len(lag)), lag]
    voiced = (ac[:, 0] > 1e-9) & (peak > 0.4 * ac[:, 0])
    if voiced.sum() < 3:
        return None
    f0 = sample_rate / lag[voiced]
    return float(np.median(12.0 * np.log2(f0 / 100.0)))


def otsu_threshold(values: list[float]) -> tuple[float, float] | None:
    """Best two-group split of 1-D values: (threshold, distance between group means)."""
    v = np.sort(np.asarray(values, dtype=np.float64))
    if len(v) < 2 or v[0] == v[-1]:
        return None
    best: tuple[float, float, float] | None = None  # (between-variance, threshold, separation)
    for k in range(1, len(v)):
        if v[k] == v[k - 1]:
            continue
        lo, hi = v[:k], v[k:]
        between = len(lo) * len(hi) * (hi.mean() - lo.mean()) ** 2
        if best is None or between > best[0]:
            best = (float(between), float((v[k - 1] + v[k]) / 2), float(hi.mean() - lo.mean()))
    return None if best is None else (best[1], best[2])


def analyze(pcm: Pcm, sample_rate: int, settings: Settings = Settings()) -> Analysis:
    duration = len(pcm) / sample_rate
    silence = silence_threshold_db(pcm, sample_rate, settings)
    raw = find_segments(pcm, sample_rate, settings)
    pitches = [tail_pitch_st(pcm, sample_rate, a, b, settings) for a, b in raw]
    split = otsu_threshold([p for p in pitches if p is not None])
    result = Analysis(
        duration, silence, None, None, [Segment(a, b, p) for (a, b), p in zip(raw, pitches, strict=True)], []
    )
    if split is None or split[1] < settings.min_cadence_separation_st:
        result.cadence_separation_st = None if split is None else split[1]
        result.warnings.append(NO_CADENCE_PATTERN)
        return result
    threshold, separation = split
    result.cadence_threshold_st, result.cadence_separation_st = threshold, separation
    segs = [Segment(a, b, p, p is not None and p < threshold) for (a, b), p in zip(raw, pitches, strict=True)]
    result.segments = segs
    offset = _half_verse_offset(segs, settings, result)
    result.parts = _group(segs, duration, settings, offset, result.warnings)
    return result


def _half_verse_offset(segs: list[Segment], settings: Settings, result: Analysis) -> int:
    """0: the cadence line ends the half-verse; 1: the line after it does (FR-AS-04).

    auto: for each cadence compare the pause after it with the pause after the next line; the half-verse
    end is followed by the longer pause in most cases.
    """
    if settings.half_verse_end != "auto":
        result.half_verse_end = settings.half_verse_end
        return 0 if settings.half_verse_end == "cadence" else 1

    def gap(i: int) -> float:
        return segs[i + 1].start_s - segs[i].end_s

    votes = [
        gap(i + 1) > gap(i)
        for i, s in enumerate(segs[:-2])
        if s.cadence and not segs[i + 1].cadence and abs(gap(i + 1) - gap(i)) >= settings.min_vote_diff_s
    ]
    share_next = sum(votes) / len(votes) if votes else 0.5
    offset = 1 if share_next > 0.5 else 0
    result.half_verse_end = "next" if offset else "cadence"
    result.half_verse_vote = share_next if offset else 1.0 - share_next
    if result.half_verse_vote < settings.min_half_verse_vote:
        result.warnings.append(HALF_VERSE_END_UNCERTAIN)
    return offset


def _group(segs: list[Segment], duration: float, settings: Settings, offset: int, warnings: list[str]) -> list[Part]:
    """A sloka ends `offset` lines after every per_sloka-th cadence; cut mid-pause (FR-AS-04, 05).

    A line broken by a breath shows up as two segments with an unusually short pause between them; such a
    pause never ends a sloka (or starts the first one).
    """
    per_sloka = settings.half_verses_per_sloka
    cad = [i for i, s in enumerate(segs) if s.cadence]
    last = len(segs) - 1

    def gap(i: int) -> float:
        return segs[i + 1].start_s - segs[i].end_s

    def cut_after(i: int) -> float:  # middle of the pause after segment i
        return duration if i >= last else (segs[i].end_s + segs[i + 1].start_s) / 2

    # typical pause between the two lines of a half-verse: after the cadence line ("next" style) or
    # before it ("cadence" style)
    if offset:
        inner = [gap(i) for i in cad if i < last and not segs[i + 1].cadence]
    else:
        inner = [gap(i - 1) for i in cad if i > 0 and not segs[i - 1].cadence]
    breath = settings.breath_gap_ratio * float(np.median(inner)) if inner else 0.0

    def end_of_line(i: int) -> int:
        while i < last and not segs[i + 1].cadence and gap(i) < breath:
            i += 1
        return i

    first = max(0, cad[0] - 1 + offset)  # first line of the first half-verse
    while first > 0 and not segs[first - 1].cadence and gap(first - 1) < breath:
        first -= 1
    ends = [
        end_of_line(min(last, cad[min(k + per_sloka, len(cad)) - 1] + offset)) for k in range(0, len(cad), per_sloka)
    ]
    if len(cad) % per_sloka:
        warnings.append(INCOMPLETE_LAST_SLOKA)

    parts: list[Part] = []
    start_t = 0.0
    if first > 0:
        start_t = cut_after(first - 1)
        parts.append(Part("intro", 0, 0.0, start_t, first, 0))
    seg_from = first
    for n, end_seg in enumerate(ends, start=1):
        end_t = cut_after(end_seg)
        cadences = sum(1 for i in cad if seg_from <= i <= end_seg)
        parts.append(Part("sloka", n, start_t, end_t, end_seg + 1 - seg_from, cadences))
        start_t, seg_from = end_t, end_seg + 1
    if seg_from < len(segs):
        parts.append(Part("closing", 0, start_t, duration, len(segs) - seg_from, 0))
    return parts
