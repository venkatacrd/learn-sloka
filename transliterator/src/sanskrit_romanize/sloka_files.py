"""One text file per sloka (FR-TR-16)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DUPLICATE_SLOKA_NUMBERS = "duplicate_sloka_numbers"
_LAST_NUMBER = re.compile(r"(\d+)\D*$")


@dataclass
class Sloka:
    number: int
    dev: list[str]
    iast: list[str]
    telugu: list[str] = field(default_factory=list)  # empty when the telugu script was not produced


@dataclass
class SlokaSet:
    slokas: list[Sloka] = field(default_factory=list)
    skipped: list[dict[str, Any]] = field(default_factory=list)  # units not written as a sloka file
    duplicates: list[int] = field(default_factory=list)


def _number(rec: dict[str, Any]) -> int | None:
    ref = rec["extracted"].get("verse_ref") or {}
    m = _LAST_NUMBER.search(str(ref.get("normalized") or ""))
    return int(m.group(1)) if m else None


def _lines(rec: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    rl = rec["romanized_lines"]
    return list(rec["extracted"]["lines"]), list(rl["iast"]), list(rl.get("telugu", []))


def collect(records: list[dict[str, Any]]) -> SlokaSet:
    out = SlokaSet()
    pending: tuple[list[str], list[str], list[str]] | None = None  # speaker line waiting for its verse
    for i, rec in enumerate(records):
        ex = rec["extracted"]
        kind = ex["unit_type"]
        if kind == "speaker":
            prev = records[i - 1]["extracted"] if i else None
            split = prev is not None and prev["unit_type"] == "verse" and "split_by_speaker" in prev["quality"]["flags"]
            if split and out.slokas and out.slokas[-1].number == _number(records[i - 1]):
                dev, iast, tel = _lines(rec)  # speaker printed inside the previous verse
                last = out.slokas[-1]
                last.dev[1:1], last.iast[1:1], last.telugu[1:1] = dev, iast, tel
            else:
                pending = _lines(rec)
            continue
        number = _number(rec) if kind == "verse" else None
        if number is None:
            out.skipped.append({"unit_id": ex["unit_id"], "unit_type": kind, "text": ex["text"][:80]})
            pending = None
            continue
        dev, iast, tel = _lines(rec)
        if pending:
            dev, iast, tel = pending[0] + dev, pending[1] + iast, pending[2] + tel
            pending = None
        out.slokas.append(Sloka(number, dev, iast, tel))
    numbers = [s.number for s in out.slokas]
    out.duplicates = sorted({n for n in numbers if numbers.count(n) > 1})
    return out


def write_sloka_files(folder: Path, prefix: str, slokas: list[Sloka], include_source: bool = True) -> list[Path]:
    """Blocks separated by a blank line: Devanagari (unless include_source=False), Telugu (if produced), IAST."""
    folder.mkdir(parents=True, exist_ok=True)
    width = max(2, len(str(max((s.number for s in slokas), default=0))))
    paths = []
    for s in slokas:
        path = folder / f"{prefix}{s.number:0{width}d}.txt"
        blocks = [s.dev] if include_source else []
        blocks += [b for b in (s.telugu, s.iast) if b]
        lines = [ln for k, b in enumerate(blocks) for ln in ([""] if k else []) + b]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        paths.append(path)
    return paths
