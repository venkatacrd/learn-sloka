"""One test per AC-TR-xx (constitution 2)."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from sanskrit_romanize.cli import app
from sanskrit_romanize.config import Config
from sanskrit_romanize.engines.sanscript_engine import SanscriptEngine
from sanskrit_romanize.io import dumps, process_file, write
from sanskrit_romanize.unit import romanize_unit
from tests.conftest import EXTRACTOR, REFERENCE_PDF, unit, write_jsonl

ENGINE = SanscriptEngine()


class CorruptEngine(SanscriptEngine):
    def from_devanagari(self, text: str, scheme: str) -> str:
        return super().from_devanagari(text, scheme).replace("kṣ", "ks")


def test_AC_TR_03_default_has_only_iast() -> None:
    rec = romanize_unit(unit(text="कृष्णः"), Config(), ENGINE)
    assert list(rec["romanized"]) == ["iast"]
    assert rec["romanized"]["iast"] == "kṛṣṇaḥ"


def test_AC_TR_06_corrupted_engine_output_fails_round_trip() -> None:
    rec = romanize_unit(unit(), Config(), CorruptEngine())
    assert rec["transliteration"]["roundtrip_ok"] is False
    assert any(w.startswith("roundtrip_mismatch at ") for w in rec["transliteration"]["warnings"])


def test_AC_TR_07_colophon_and_latin_unit() -> None:
    rec = romanize_unit(unit(unit_type="heading", verse_ref=None, text="इति प्रथमोऽध्यायः"), Config(), ENGINE)
    assert rec["romanized"]["iast"] == "iti prathamo'dhyāyaḥ"
    latin = unit(unit_type="other", verse_ref=None, text="Chapter One", script="latin")
    rec = romanize_unit(latin, Config(), ENGINE)
    assert rec["transliteration"]["skipped"] is True
    assert rec["romanized"]["iast"] == "Chapter One"
    assert rec["transliteration"]["warnings"]


def test_AC_TR_16_mixed_script_unit() -> None:
    text = "गीताध्यानश्लोकाः ..... i"
    rec = romanize_unit(unit(unit_type="heading", verse_ref=None, text=text, script="mixed"), Config(), ENGINE)
    assert rec["romanized"]["iast"] == "gītādhyānaślokāḥ ..... i"
    assert rec["transliteration"]["skipped"] is False
    assert rec["transliteration"]["roundtrip_ok"] is True
    assert "latin_text_kept" in rec["transliteration"]["warnings"]


def test_AC_TR_08_lines_aligned_for_every_scheme() -> None:
    rec = romanize_unit(unit(), Config(schemes=["iast", "hk", "ascii"]), ENGINE)
    for scheme, lines in rec["romanized_lines"].items():
        assert len(lines) == len(rec["extracted"]["lines"]), scheme


def test_AC_TR_09_citation() -> None:
    ex = unit(verse_ref={"label": "॥ २-४७ ॥", "normalized": "2.47"})
    ex["source"] |= {"page_start": 34, "page_end": 34}
    assert romanize_unit(ex, Config(), ENGINE)["rag"]["citation"] == "gita.pdf p.34, verse 2.47"


def test_AC_TR_10_vedic_accent_kept_with_warning() -> None:
    rec = romanize_unit(unit(text="अ॒ग्निमी॑ळे पु॒रोहि॑तम्"), Config(), ENGINE)
    assert "॑" in rec["romanized"]["iast"]
    assert "vedic_accents_unsupported" in rec["transliteration"]["warnings"]
    assert rec["transliteration"]["roundtrip_ok"] is True


def test_AC_TR_11_invalid_line_reported_rest_processed(tmp_path: Path) -> None:
    src = write_jsonl(
        tmp_path / "in.jsonl",
        [unit(), unit(unit_id="gita-1a2b3c4d:000002", seq=2)],
        extra_lines=['{"not": "a unit"}', "{broken json"],
    )
    result = CliRunner().invoke(app, [str(src), "-o", str(tmp_path / "out")])
    assert result.exit_code == 1
    report = json.loads(next((tmp_path / "out").glob("*.report.json")).read_text())
    assert report["units_out"] == 2
    assert [x["line"] for x in report["invalid_lines"]] == [3, 4]


def test_AC_TR_12_deterministic_valid_and_input_unchanged(tmp_path: Path) -> None:
    src = write_jsonl(tmp_path / "in.jsonl", [unit()])
    a, b = process_file(src, Config(), ENGINE), process_file(src, Config(), ENGINE)
    write(tmp_path / "a", a)
    write(tmp_path / "b", b)
    for f in (tmp_path / "a").iterdir():
        assert f.read_bytes() == (tmp_path / "b" / f.name).read_bytes()
    assert dumps(a.records[0]["extracted"]) == dumps(unit())  # NFR-TR-04


def test_strict_ignores_source_invalid_units(tmp_path: Path) -> None:
    bad = unit(text="ध्रुृवम्", lines=["ध्रुृवम्"])
    bad["quality"]["flags"] = ["invalid_syllables", "needs_review"]
    src = write_jsonl(tmp_path / "in.jsonl", [unit(), bad | {"unit_id": "gita-1a2b3c4d:000002", "seq": 2}])
    result = CliRunner().invoke(app, [str(src), "-o", str(tmp_path / "o"), "--strict"])
    assert result.exit_code == 0
    report = json.loads(next((tmp_path / "o").glob("*.report.json")).read_text())
    assert report["roundtrip_failures"] == []
    assert [x["unit_id"] for x in report["source_invalid"]] == ["gita-1a2b3c4d:000002"]


def test_AC_TR_15_readable_text(tmp_path: Path) -> None:
    src = write_jsonl(tmp_path / "in.jsonl", [unit()])
    write(tmp_path / "o", process_file(src, Config(), ENGINE))
    txt = next((tmp_path / "o").glob("*.romanized.txt")).read_text(encoding="utf-8")
    body = txt.splitlines()
    i = body.index("धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः ।")
    assert body[i + 2] == "dharmakṣetre kurukṣetre samavetā yuyutsavaḥ |"


@pytest.mark.e2e
def test_AC_TR_13_and_AC_TR_05_end_to_end(tmp_path: Path) -> None:
    """Extractor CLI on the reference PDF, then the transliterator: every verse has IAST and round-trips."""
    if not REFERENCE_PDF.exists() or not EXTRACTOR.exists():
        pytest.skip("reference PDF or pdf-extractor project missing")
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"} | {"UV_NO_EDITABLE": "1"}
    subprocess.run(
        ["uv", "run", "-q", "sanskrit-extract", str(REFERENCE_PDF), "-o", str(tmp_path / "ex")],
        cwd=EXTRACTOR,
        env=env,
        check=True,
    )
    results = [process_file(p, Config(), ENGINE) for p in sorted((tmp_path / "ex").glob("*.jsonl"))]
    records: list[dict[str, Any]] = [r for res in results for r in res.records]
    verses = [r for r in records if r["extracted"]["unit_type"] == "verse"]
    assert len(verses) == 47
    assert all(r["romanized"]["iast"] and r["transliteration"]["roundtrip_ok"] for r in records)


def test_cross_check_engine_agrees_on_gita_verse() -> None:
    pytest.importorskip("aksharamukha")
    from sanskrit_romanize.engines.aksharamukha_engine import AksharamukhaEngine

    rec = romanize_unit(unit(), Config(), ENGINE, AksharamukhaEngine())
    assert not [w for w in rec["transliteration"]["warnings"] if w.startswith("cross_check")]


def test_AC_TR_17_page_selection(tmp_path: Path) -> None:
    def on(seq: int, start: int, end: int) -> dict[str, Any]:
        src = {"file_name": "gita.pdf", "sha256": "0" * 64, "page_start": start, "page_end": end}
        return unit(seq=seq, unit_id=f"gita-1a2b3c4d:{seq:06d}", source=src)

    path = write_jsonl(tmp_path / "in.jsonl", [on(1, 1, 1), on(2, 1, 2), on(3, 2, 2), on(4, 3, 3)])
    out = tmp_path / "out"
    r = CliRunner().invoke(app, [str(path), "-o", str(out), "--pages", "2"])
    assert r.exit_code == 0, r.output
    rows = [json.loads(x) for x in (out / "gita-1a2b3c4d.romanized.jsonl").read_text().splitlines()]
    assert [x["extracted"]["seq"] for x in rows] == [2, 3]  # the unit spanning pages 1-2 is included
    rep = json.loads((out / "gita-1a2b3c4d.romanized.report.json").read_text())
    assert rep["units_in"] == rep["units_out"] == 2 and rep["units_outside_pages"] == 2
    assert rep["pages_selected"] == "2"

    r = CliRunner().invoke(app, [str(path), "-o", str(tmp_path / "o2"), "--pages", "2-"])
    rows = (tmp_path / "o2" / "gita-1a2b3c4d.romanized.jsonl").read_text().splitlines()
    assert r.exit_code == 0 and len(rows) == 3
    for bad in ("0", "3-1", "x"):
        assert CliRunner().invoke(app, [str(path), "-o", str(tmp_path / "o3"), "--pages", bad]).exit_code == 2


def _deva(n: int) -> str:
    return str(n).translate(str.maketrans("0123456789", "०१२३४५६७८९"))


def _chapter(tmp_path: Path, numbers: list[int], dup: bool = False) -> Path:
    """Heading, speaker + verse 1, verse 2 split by a speaker, verse 3 ... on page = verse number."""
    units: list[dict[str, Any]] = []

    def add(kind: str, lines: list[str], page: int, ref: int | None = None, flags: list[str] | None = None) -> None:
        seq = len(units) + 1
        src = {"file_name": "gita.pdf", "sha256": "0" * 64, "page_start": page, "page_end": page}
        units.append(
            unit(
                seq=seq,
                unit_id=f"gita-1a2b3c4d:{seq:06d}",
                unit_type=kind,
                text=" ".join(lines),
                lines=lines,
                verse_ref=None if ref is None else {"label": f"॥ {_deva(ref)} ॥", "normalized": str(ref)},
                quality={"score": 1.0, "ocr_confidence": None, "flags": flags or []},
                source=src,
            )
        )

    add("heading", ["॥ अथ प्रथमोऽध्यायः ॥"], 1)
    for n in numbers:
        if n == 1:
            add("speaker", ["सञ्जय उवाच -"], n)
        verse = ["धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः ।", f"मामकाः पाण्डवाश्चैव किमकुर्वत सञ्जय ॥ {_deva(n)} ॥"]
        add("verse", verse, n, n, ["split_by_speaker"] if n == 2 else None)
        if n == 2:
            add("speaker", ["अर्जुन उवाच -"], n)
    if dup:
        add("verse", ["धर्मक्षेत्रे कुरुक्षेत्रे ।", "मामकाः सञ्जय ॥ १ ॥"], 99, 1)
    add("heading", ["॥ इति प्रथमोऽध्यायः ॥"], 99)
    return write_jsonl(tmp_path / "in.jsonl", units)


def test_AC_TR_18_one_file_per_sloka(tmp_path: Path) -> None:
    src = _chapter(tmp_path, list(range(1, 12)))
    out = tmp_path / "out"
    r = CliRunner().invoke(app, [str(src), "-o", str(out), "--sloka-prefix", "1_Ch_01_Complete_sloka_"])
    assert r.exit_code == 0, r.output
    names = sorted(p.name for p in (out / "slokas").iterdir())
    assert names == [f"1_Ch_01_Complete_sloka_{n:02d}.txt" for n in range(1, 12)]
    one = (out / "slokas" / "1_Ch_01_Complete_sloka_01.txt").read_text(encoding="utf-8").splitlines()
    assert one[0] == "सञ्जय उवाच -" and "sañjaya uvāca -" in one and "" in one
    two = (out / "slokas" / "1_Ch_01_Complete_sloka_02.txt").read_text(encoding="utf-8").splitlines()
    assert two[1] == "अर्जुन उवाच -" and two[two.index("") + 2] == "arjuna uvāca -"
    three = (out / "slokas" / "1_Ch_01_Complete_sloka_03.txt").read_text(encoding="utf-8")
    assert "उवाच" not in three
    rep = json.loads((out / "gita-1a2b3c4d.romanized.report.json").read_text())
    assert rep["sloka_files"]["written"] == 11
    assert [s["unit_type"] for s in rep["sloka_files"]["skipped"]] == ["heading", "heading"]

    sub = tmp_path / "sub"
    r = CliRunner().invoke(app, [str(src), "-o", str(sub), "--sloka-files", "--pages", "6-9"])
    assert r.exit_code == 0, r.output
    assert sorted(p.name for p in (sub / "slokas").iterdir()) == [f"sloka_{n:02d}.txt" for n in range(6, 10)]


def test_AC_TR_18_duplicate_numbers(tmp_path: Path) -> None:
    src = _chapter(tmp_path, [1, 2, 3], dup=True)
    out = tmp_path / "out"
    r = CliRunner().invoke(app, [str(src), "-o", str(out), "--sloka-files"])
    assert r.exit_code == 1 and "sloka numbers repeat (1)" in r.output
    assert not (out / "slokas").exists()
    rep = json.loads((out / "gita-1a2b3c4d.romanized.report.json").read_text())
    assert rep["sloka_files"]["error"] == "duplicate_sloka_numbers"


def test_AC_TR_19_sloka_files_without_source(tmp_path: Path) -> None:
    import re

    src = _chapter(tmp_path, [1, 2, 3])
    full, iast = tmp_path / "full", tmp_path / "iast"
    assert CliRunner().invoke(app, [str(src), "-o", str(full), "--sloka-files"]).exit_code == 0
    r = CliRunner().invoke(app, [str(src), "-o", str(iast), "--sloka-files", "--sloka-no-source"])
    assert r.exit_code == 0, r.output
    one = (iast / "slokas" / "sloka_01.txt").read_text(encoding="utf-8")
    assert not re.search("[ऀ-ॿ]", one) and "\n\n" not in one
    assert one.splitlines()[0] == "sañjaya uvāca -" and len(one.splitlines()) == 3
    two = (iast / "slokas" / "sloka_02.txt").read_text(encoding="utf-8").splitlines()
    assert two[1] == "arjuna uvāca -"
    for name in ("gita-1a2b3c4d.romanized.jsonl", "gita-1a2b3c4d.romanized.txt"):
        assert (full / name).read_bytes() == (iast / name).read_bytes()
