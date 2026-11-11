import json
import time
from pathlib import Path

import pytest

from sloka_split.splitter import split_path

REFERENCE = Path(__file__).resolve().parents[2] / "1_Ch 01 Complete.mp3"


@pytest.mark.e2e
@pytest.mark.skipif(not REFERENCE.exists(), reason="reference recording not present")
def test_AC_AS_10_reference_chapter_1(tmp_path: Path) -> None:
    t = time.perf_counter()
    [r] = split_path(REFERENCE, tmp_path, expected=47)
    assert time.perf_counter() - t < 10
    assert r.warnings == []
    assert r.sloka_count == 47
    assert r.parts[0].kind == "intro" and r.parts[-1].kind == "closing"
    assert all(p.cadences == 2 for p in r.parts if p.kind == "sloka")
    report = json.loads((tmp_path / "1_Ch_01_Complete.splits.json").read_text())
    # this reciter's pitch falls on lines 1 and 3; lines 2 and 4 (longer pause after) end each half-verse
    assert report["half_verse_end"] == "next" and report["half_verse_end_vote"] > 0.7
