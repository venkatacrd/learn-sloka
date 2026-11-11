"""Split MP3 files into per-sloka files and write the reports (FR-AS-01, 06..11, NFR-AS-01, 02)."""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path

import miniaudio
import numpy as np
from mutagen.id3 import ID3, TALB, TIT2, TRCK

from . import __version__
from .analysis import (
    HALF_VERSE_END_UNCERTAIN,
    INCOMPLETE_LAST_SLOKA,
    NO_CADENCE_PATTERN,
    Analysis,
    Part,
    Settings,
    analyze,
)
from .mp3frames import Mp3Audio, parse
from .review import TEXT_UNREADABLE, load_sloka_text, render

ANALYSIS_RATE = 16000
COUNT_MISMATCH = "count_mismatch"
COVERAGE_FAILED = "coverage_failed"
DOUBTFUL = {NO_CADENCE_PATTERN, INCOMPLETE_LAST_SLOKA, HALF_VERSE_END_UNCERTAIN, COUNT_MISMATCH, COVERAGE_FAILED}


class UnsafeOutputError(ValueError):
    """Refusing to clean an output folder that could hold the inputs or other important files."""


@dataclass(frozen=True)
class WrittenPart:
    name: str
    kind: str
    number: int
    start_s: float
    end_s: float
    duration_s: float
    frames: tuple[int, int]
    segments: int
    cadences: int


@dataclass
class FileResult:
    source: Path
    parts: list[WrittenPart] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def sloka_count(self) -> int:
        return sum(1 for p in self.parts if p.kind == "sloka")

    @property
    def doubtful(self) -> bool:
        return any(w in DOUBTFUL for w in self.warnings)


def collect_inputs(path: Path) -> list[Path]:
    if path.is_dir():
        return sorted(p for p in path.iterdir() if p.is_file() and p.suffix.lower() == ".mp3")
    if path.is_file():
        return [path]
    raise FileNotFoundError(path)


def prepare_output(out: Path, inputs: list[Path], clean: bool) -> None:
    """Create the output folder; with clean=True first empty it, refusing dangerous folders (FR-AS-11)."""
    out = out.expanduser().resolve()
    if clean and out.exists():
        if out == Path(out.anchor) or out == Path.home().resolve():
            raise UnsafeOutputError(f"refusing to clean {out}")
        for src in inputs:
            folder = src.resolve().parent
            if folder == out or out in folder.parents:
                raise UnsafeOutputError(f"refusing to clean {out}: it contains the input {src}")
        for child in sorted(out.iterdir()):
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()
    out.mkdir(parents=True, exist_ok=True)


def file_stem(src: Path) -> str:
    return src.stem.replace(" ", "_")


def part_name(stem: str, part: Part, width: int) -> str:
    if part.kind == "sloka":
        return f"{stem}_sloka_{part.number:0{width}d}"
    return f"{stem}_{part.kind}"


def decode_mono(data: bytes) -> np.ndarray:
    d = miniaudio.decode(data, output_format=miniaudio.SampleFormat.FLOAT32, nchannels=1, sample_rate=ANALYSIS_RATE)
    return np.frombuffer(d.samples, dtype=np.float32)


def _tag(path: Path, title: str, track: str | None, album: str) -> None:
    tags = ID3()
    tags.add(TIT2(encoding=3, text=title))
    tags.add(TALB(encoding=3, text=album))
    if track:
        tags.add(TRCK(encoding=3, text=track))
    tags.save(path, v2_version=3, padding=lambda info: 0)


def _title(part: Part) -> str:
    return f"Sloka {part.number}" if part.kind == "sloka" else part.kind.capitalize()


def _r(x: float) -> float:
    return round(x, 3)


def split_file(
    src: Path,
    out: Path,
    settings: Settings = Settings(),
    expected: int | None = None,
    text: dict[int, dict[str, list[str]]] | None = None,
) -> FileResult:
    data = src.read_bytes()
    audio = parse(data)
    analysis = analyze(decode_mono(data), ANALYSIS_RATE, settings)
    result = FileResult(src, warnings=list(analysis.warnings))
    stem = file_stem(src)
    n_slokas = len(analysis.slokas)
    width = max(2, len(str(n_slokas)))

    for part in analysis.parts:
        f0, f1 = audio.frame_at(part.start_s), audio.frame_at(part.end_s)
        if part is analysis.parts[-1]:
            f1 = audio.frame_count
        if f1 <= f0:
            continue
        name = part_name(stem, part, width)
        path = out / f"{name}.mp3"
        path.write_bytes(audio.frame_bytes(f0, f1))
        track = f"{part.number}/{n_slokas}" if part.kind == "sloka" else None
        _tag(path, _title(part), track, src.name)
        t0, t1 = f0 * audio.samples_per_frame / audio.sample_rate, f1 * audio.samples_per_frame / audio.sample_rate
        result.parts.append(
            WrittenPart(
                name, part.kind, part.number, _r(t0), _r(t1), _r(t1 - t0), (f0, f1), part.segments, part.cadences
            )
        )

    if expected is not None and n_slokas != expected:
        result.warnings.append(COUNT_MISMATCH)
    if result.parts and not _coverage_ok(audio, [out / f"{p.name}.mp3" for p in result.parts]):
        result.warnings.append(COVERAGE_FAILED)
    _write_reports(out, stem, src, audio, analysis, settings, expected, result)
    _write_review(out, stem, src, result, text or {})
    return result


def _write_review(out: Path, stem: str, src: Path, result: FileResult, text: dict[int, dict[str, list[str]]]) -> None:
    """FR-AS-14: offline page to check every cut by ear."""
    parts = [
        {
            "file": f"{p.name}.mp3",
            "kind": p.kind,
            "number": p.number,
            "start_s": p.start_s,
            "end_s": p.end_s,
            "duration_s": p.duration_s,
        }
        for p in result.parts
    ]
    (out / f"{stem}.review.html").write_text(render(src.name, parts, text), encoding="utf-8")


def _coverage_ok(audio: Mp3Audio, files: list[Path]) -> bool:
    """NFR-AS-01: the written files' audio frames, joined, equal the source's audio frames."""
    joined = b"".join(parse(f.read_bytes()).audio_bytes() for f in files)
    return joined == audio.audio_bytes()


def _write_reports(
    out: Path,
    stem: str,
    src: Path,
    audio: Mp3Audio,
    analysis: Analysis,
    settings: Settings,
    expected: int | None,
    result: FileResult,
) -> None:
    report = {
        "tool": "sloka-split",
        "version": __version__,
        "source": src.name,
        "duration_s": _r(audio.duration_s),
        "settings": asdict(settings),
        "expected_slokas": expected,
        "slokas": result.sloka_count,
        "segments": len(analysis.segments),
        "cadences": sum(1 for s in analysis.segments if s.cadence),
        "cadence_threshold_hz": None
        if analysis.cadence_threshold_st is None
        else _r(100 * 2 ** (analysis.cadence_threshold_st / 12)),
        "cadence_separation_semitones": None
        if analysis.cadence_separation_st is None
        else _r(analysis.cadence_separation_st),
        "half_verse_end": analysis.half_verse_end,
        "half_verse_end_vote": None if analysis.half_verse_vote is None else _r(analysis.half_verse_vote),
        "warnings": result.warnings,
        "parts": [
            {
                "file": f"{p.name}.mp3",
                "kind": p.kind,
                "number": p.number,
                "start_s": p.start_s,
                "end_s": p.end_s,
                "duration_s": p.duration_s,
                "frames": list(p.frames),
                "segments": p.segments,
                "cadences": p.cadences,
            }
            for p in result.parts
        ],
    }
    (out / f"{stem}.splits.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    labels = "".join(f"{p.start_s:.3f}\t{p.end_s:.3f}\t{p.name}\n" for p in result.parts)
    (out / f"{stem}.labels.txt").write_text(labels, encoding="utf-8")


def split_path(
    path: Path,
    out: Path,
    *,
    clean: bool = False,
    settings: Settings = Settings(),
    expected: int | None = None,
    text_path: Path | None = None,
) -> list[FileResult]:
    inputs = collect_inputs(path)
    prepare_output(out, inputs, clean)
    text: dict[int, dict[str, list[str]]] = {}
    text_warning: list[str] = []
    if text_path is not None:
        try:
            text = load_sloka_text(text_path)
        except (OSError, ValueError, KeyError, TypeError):
            text_warning = [TEXT_UNREADABLE]
    results = [split_file(src, out, settings, expected, text) for src in inputs]
    for r in results:
        r.warnings.extend(text_warning)
    return results
