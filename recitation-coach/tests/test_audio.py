"""Acceptance on real audio: the author's three takes and the instructor's 47 slokas (skip if absent)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from recite_coach import model
from recite_coach.cli import check_app
from recite_coach.coach import Coach
from tests.conftest import AUDIO, TAKES, TEXT

needs = pytest.mark.skipif(
    TEXT is None or not AUDIO.is_dir() or bool(model.missing_or_bad()),
    reason="needs the book in output/pdf/, chapter 1 in output/mp3/, and the model (recite-setup)",
)
takes_needed = pytest.mark.skipif(not TAKES.is_dir(), reason="input/recordings/ (author's takes) not present")


@pytest.fixture(scope="module")
def coach() -> Coach:
    assert TEXT is not None
    return Coach.open(TEXT, AUDIO)


def _reported(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [f for f in result["findings"] if f["reported"]]


@needs
@takes_needed
def test_AC_RC_05_author_takes(coach: Coach) -> None:
    expected = {  # confirmed by the author (2026-11-11): (pada, expected letter(s), heard letter(s))
        "chapter1-sloka1-test.mp3": [(2, "त", "द"), (3, "ा", "")],
        "take 1 - fail.mp3": [(3, "ड", "द")],
        "take 3 - error.mp3": [(4, "त", "क")],
    }
    for name, must in expected.items():
        result = coach.check(1, 1, model.load_audio(TAKES / name))
        rep = _reported(result)
        padas = {f["pada"] for f in rep}
        assert 1 not in padas, (name, rep)  # line 1 was recited correctly
        assert padas & {2, 3, 4}, name
        got = {(f["pada"], f["expected"], f["heard"]) for f in rep}
        for item in must:
            assert item in got, (name, item, got)
    # every take: something reported in lines 2 and 3; line 4 in the takes where it isn't the held final vowel
    for name in ("take 1 - fail.mp3", "take 3 - error.mp3"):
        padas = {f["pada"] for f in _reported(coach.check(1, 1, model.load_audio(TAKES / name)))}
        assert {2, 3, 4} <= padas, (name, padas)


@needs
def test_AC_RC_06_instructor_false_alarms(coach: Coach) -> None:
    total = 0
    slokas = coach.chapters[1].slokas
    for n, s in slokas.items():
        assert s.audio is not None
        total += len(_reported(coach.check(1, n, model.load_audio(s.audio))))
    assert total / len(slokas) <= 1.0, total


@needs
@takes_needed
def test_AC_RC_08_word_times(coach: Coach) -> None:
    result = coach.check(1, 1, model.load_audio(TAKES / "take 1 - fail.mp3"))
    f = next(f for f in result["findings"] if f["word_iast"].startswith("pāṇḍav"))
    (a, b), (ta, tb) = f["span"], f["teacher_span"]
    assert 0 <= a < b and 0 <= ta < tb
    # pāṇḍavāścaiva is the 2nd word of line 3: after line 2's words in both recordings
    line2 = next(ln for ln in result["lines"] if ln["pada"] == 2)
    assert a > max(w["span"][1] for w in line2["words"] if w["span"]) - 0.2
    assert ta > max(w["teacher_span"][1] for w in line2["words"] if w["teacher_span"]) - 0.2


@needs
@takes_needed
def test_AC_RC_09_cli_json(tmp_path: Path) -> None:
    assert TEXT is not None
    take = str(TAKES / "take 1 - fail.mp3")
    args = [take, "--chapter", "1", "--sloka", "1", "--text", str(TEXT), "--audio", str(AUDIO), "--json"]
    r = CliRunner().invoke(check_app, args)
    assert r.exit_code == 1, r.output
    out = json.loads(r.stdout)
    assert out["sloka"] == 1 and out["counts"]["reported"] >= 1
    clean = next(AUDIO.glob("*_sloka_05.mp3"))  # instructor sloka with no reported finding
    r = CliRunner().invoke(check_app, [str(clean), "--chapter", "1", "--sloka", "5", "--text", str(TEXT)])
    assert r.exit_code == 0, r.output


@needs
@takes_needed
def test_AC_RC_11_same_recording_same_result(coach: Coach) -> None:
    pcm = model.load_audio(TAKES / "take 3 - error.mp3")
    assert coach.check(1, 1, pcm) == coach.check(1, 1, pcm)
