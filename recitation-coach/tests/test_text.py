"""Text-level tests: library, normalisation, comparison, feedback (no audio, no model)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from recite_coach.cli import check_app
from recite_coach.compare import compare
from recite_coach.feedback import letters_iast, to_json
from recite_coach.library import load_book, load_chapter
from recite_coach.normalize import chars_of, comparison_form, text_of
from tests.conftest import AUDIO, TEXT, heard


def norm(s: str) -> str:
    return text_of(comparison_form(chars_of(s, 0)))


def test_cli_version() -> None:
    r = CliRunner().invoke(check_app, ["--version"])
    assert r.exit_code == 0 and r.stdout.strip() == "0.1.0"


def test_AC_RC_01_library_padas_and_speakers(chapter: Path) -> None:
    s = load_chapter(chapter, None)
    assert sorted(s) == [1, 21]
    one = s[1].lines
    assert one[0].speaker and one[0].dev == "धृतराष्ट्र उवाच"
    assert [ln.pada for ln in one] == [0, 1, 2, 3, 4]
    assert one[1].dev == "धर्मक्षेत्रे कुरुक्षेत्रे" and one[4].iast == "kimakurvata sañjaya"
    assert [(ln.pada, ln.speaker) for ln in s[21].lines] == [(1, False), (2, False), (0, True), (3, False), (4, False)]
    assert not s[1].available  # no audio folder given


@pytest.mark.skipif(TEXT is None or not AUDIO.is_dir(), reason="book text (output/pdf/) or chapter 1 audio not present")
def test_AC_RC_01_reference_chapter(tmp_path: Path) -> None:
    assert TEXT is not None
    s = load_book(TEXT, AUDIO)[1].slokas
    assert len(s) == 47 and all(x.available for x in s.values())
    assert s[2].lines[0].dev.startswith("सञ्जय उवाच")
    assert [ln.speaker for ln in s[21].lines].index(True) == 2
    copy = tmp_path / "audio"
    shutil.copytree(AUDIO, copy)
    next(copy.glob("*_sloka_05.mp3")).unlink()
    assert not load_book(TEXT, copy)[1].slokas[5].available


def test_AC_RC_03_normalisation() -> None:
    assert norm("पुत्राणाम् आचार्य") == norm("पुत्राणामाचार्य")
    assert norm("संग") == norm("सङ्ग") and norm("सञ्जय") == norm("संजय")
    assert norm("उपसङ्गम्य") == norm("उपसङ्गंय")  # म् and ं sound alike before य र ल व श ष स ह
    assert norm("पश्यामिि") == norm("पश्यामि")  # the model sometimes repeats a vowel sign
    assert norm("धर्मक्षेत्रे ।  कुरु-क्षेत्रे ॥ १ ॥") == norm("धर्मक्षेत्रेकुरुक्षेत्रे")


def test_AC_RC_03_speaker_line_optional(chapter: Path) -> None:
    lines = load_chapter(chapter, None)[1].lines
    full = "धृतराष्ट्र उवाच धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः मामकाः पाण्डवाश्चैव किमकुर्वत सञ्जय"
    for said in (full, full.split(" ", 2)[2]):
        c = compare(lines, heard(said))
        assert c.findings == [] and c.score == 100.0
    assert not compare(lines, heard(full.split(" ", 2)[2])).speaker_compared


def _kinds(lines: list, said: str, prob: float = 0.95) -> list[tuple[str, str, bool]]:  # type: ignore[type-arg]
    c = compare(lines, heard(said, prob))
    return [(f.kind, c.words[f.word].word.iast, f.reported) for f in c.findings]


def test_AC_RC_04_kinds(chapter: Path) -> None:
    lines = load_chapter(chapter, None)[1].lines
    base = "धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः मामकाः पाण्डवाश्चैव किमकुर्वत सञ्जय"
    k = _kinds(lines, base.replace("समवेता युयुत्सवः", "समवेत युरयुत्सव"))
    assert ("vowel length", "samavetā", True) in k
    assert ("extra letter", "yuyutsavaḥ", True) in k
    assert ("visarga", "yuyutsavaḥ", False) in k  # visarga: always unsure
    assert _kinds(lines, base.replace("पाण्डवा", "पाण्दवा")) == [("retroflex/dental", "pāṇḍavāścaiva", True)]
    assert _kinds(lines, base.replace("समवेता", "समवेदा")) == [("voicing", "samavetā", True)]
    assert _kinds(lines, base.replace("कुरुक्षेत्रे", "कुरुक्सेत्रे")) == [("sibilant", "kurukṣetre", True)]
    assert _kinds(lines, base.replace("सञ्जय", "सजय")) == [("nasal", "sañjaya", True)]
    skipped = _kinds(lines, base.replace("मामकाः ", ""))
    assert [k for k in skipped if k[2]] == [("missing word", "māmakāḥ", True)]  # one finding for the whole word


def test_AC_RC_04_confidence_and_messages(chapter: Path) -> None:
    lines = load_chapter(chapter, None)[1].lines
    said = "धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः मामकाः पाण्दवाश्चैव किमकुर्वत सञ्जय"
    assert [f.reported for f in compare(lines, heard(said, prob=0.3)).findings] == [False]  # 1 letter, low prob
    out = to_json(compare(lines, heard(said)), 1)
    [f] = out["findings"]
    assert f["pada"] == 3 and f["expected_iast"] == "ḍ" and f["heard_iast"] == "d"
    assert "retroflex" in f["message"] and "dental" in f["message"]
    assert out["counts"] == {"reported": 1, "unsure": 0}
    assert letters_iast("ञ्") == "ñ" and letters_iast("ा") == "ā"


def test_AC_RC_07_accepted_variants(chapter: Path) -> None:
    lines = load_chapter(chapter, None)[1].lines
    base = "धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः मामकाः पाण्डवाश्चैव किमकुर्वत सञ्जय"
    assert _kinds(lines, base + "ा") == []  # held last vowel at the end of a line: chanting, not a mistake
    assert _kinds(lines, base.replace("कुर्वत", "कुर्वता")) == [("vowel length", "kimakurvata", True)]  # mid-line
    assert _kinds(lines, base.replace("पाण्डवा", "पाण्डवः")) == [("substituted letter", "pāṇḍavāścaiva", True)]


def test_AC_RC_11_deterministic(chapter: Path) -> None:
    lines = load_chapter(chapter, None)[1].lines
    said = heard("धर्मक्षेत्रे कुरुक्षेत्रे समवदा ययुत्सव मामकाः पाण्डवःश्चैव किमकुर्वकसञ्जया", 0.7)
    assert to_json(compare(lines, said), 1) == to_json(compare(lines, said), 1)


def test_check_cli_errors(chapter: Path, tmp_path: Path) -> None:
    rec = tmp_path / "x.wav"
    rec.write_bytes(b"not audio")
    r = CliRunner().invoke(check_app, [str(rec), "--sloka", "1", "--text", str(chapter)])
    assert r.exit_code == 2  # model missing or audio unreadable


def _mp3s(folder: Path, name: str, count: int) -> None:
    folder.mkdir(parents=True)
    for k in range(1, count + 1):
        (folder / f"{name}_sloka_{k:02d}.mp3").write_bytes(b"ID3")


def test_AC_RC_13_whole_book_chapters(book: Path, chapter: Path, tmp_path: Path) -> None:
    root = tmp_path / "mp3"
    _mp3s(root / "1_Ch 01 Complete", "1_Ch_01_Complete", 3)
    _mp3s(root / "1_CH 02 Complete", "CH02", 1)  # one file fewer than the book's 2 slokas
    _mp3s(root / "1_Ch 00 Complete", "CH00", 4)  # no such chapter in the text: ignored
    b = load_book(book, root)
    assert sorted(b) == [1, 2]  # the Mahatmya part is not a chapter
    one, two = b[1], b[2]
    assert (one.title_dev, two.title_dev, two.title_iast) == ("अर्जुनविषादयोगः", "साङ्ख्ययोगः", "साङ्ख्ययोगः-iast")
    assert sorted(one.slokas) == [1, 2, 3] and sorted(two.slokas) == [1, 2]
    assert one.slokas[1].lines[0].dev == "धृतराष्ट्र उवाच" and two.slokas[1].lines[0].dev == "सञ्जय उवाच"
    assert one.audio_matches and all(s.available for s in one.slokas.values())
    assert two.audio_parts == 1 and not two.audio_matches
    assert two.slokas[1].available and not two.slokas[2].available
    assert list(load_book(chapter, None)) == [1]  # a chapter text without "अथ … अध्यायः" headings
    assert load_book(book, root / "1_CH 02 Complete")[2].audio_parts == 1  # a single chapter folder
