"""One test per AC-EX-xx (constitution 2). Generated fixtures + the reference PDF (Q1a)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from sanskrit_extract import cli
from sanskrit_extract.config import Config
from sanskrit_extract.models import PageClass
from sanskrit_extract.ocr import doctor
from sanskrit_extract.pdf_reader import PdfDocument
from sanskrit_extract.pipeline import extract, plan_pages, run_batch
from tests.conftest import GOLD_DIR, assert_valid_unit, gold_pages
from tests.fixtures.factory import FakeEngine, Image, Rule, T, gold, make_pdf, verse_lines


def _no_ocr() -> Any:
    raise AssertionError("OCR must not be called")


def _types(units: list[dict[str, Any]]) -> list[str]:
    return [u["unit_type"] for u in units]


@pytest.fixture
def mixed_pdf(tmp_path: Path) -> Path:
    """5 text-layer pages + 2 scanned pages."""
    pages: list[Any] = [verse_lines(n, 100) for n in range(1, 6)]
    pages += [Image(tuple(verse_lines(6, 100))), Image(tuple(verse_lines(7, 100)))]
    return make_pdf(tmp_path / "mixed.pdf", pages)


# --- generated fixtures ---------------------------------------------------------------------------


def test_AC_EX_01_batch_with_corrupt_file(tmp_path: Path) -> None:
    src = tmp_path / "in"
    src.mkdir()
    make_pdf(src / "a.pdf", [verse_lines(1, 100)])
    make_pdf(src / "b.pdf", [verse_lines(2, 100)])
    (src / "c.pdf").write_bytes(b"not a pdf at all")
    out = tmp_path / "out"
    result = CliRunner().invoke(cli.app, [str(src), "-o", str(out)])
    assert result.exit_code == 1
    assert len(list(out.glob("*.jsonl"))) == 2
    assert len(list(out.glob("*.report.json"))) == 2
    assert "c.pdf" in result.output


def test_AC_EX_02_unicode_text_layer(tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "g.pdf", [verse_lines(1, 100)])
    with PdfDocument(pdf) as doc:
        assert plan_pages(doc, Config())[0].page_class is PageClass.TEXT_LAYER_OK
    units = extract(pdf, Config(), _no_ocr).units
    assert units[0]["text"] == gold("gita_1_1")
    assert units[0]["extraction"]["method"] == "text_layer"


def test_AC_EX_03_reordered_matras_go_to_ocr(tmp_path: Path) -> None:
    broken = "िवजय िकम िशव ि◌न ाम ाक धर्म"  # short-i stored before its consonant, as broken PDFs do
    pdf = make_pdf(tmp_path / "b.pdf", [[T(broken, 100), T(broken, 120)]])
    with PdfDocument(pdf) as doc:
        assert plan_pages(doc, Config())[0].page_class is PageClass.TEXT_LAYER_BROKEN
    engine = FakeEngine()
    units = extract(pdf, Config(), lambda: engine).units
    assert engine.calls == 1
    assert {u["extraction"]["method"] for u in units} == {"ocr"}


def test_AC_EX_07_verse_across_pages(tmp_path: Path) -> None:
    first, second = verse_lines(9, 0)
    pages: list[Any] = [verse_lines(n, 100) for n in range(1, 4)]
    pages.append([*verse_lines(4, 100), T(first.text, 700)])
    pages.append([T(second.text, 100)])
    units = extract(make_pdf(tmp_path / "x.pdf", pages), Config(), _no_ocr).units
    last = units[-1]
    assert last["source"]["page_start"] == 4
    assert last["source"]["page_end"] == 5
    assert "crosses_page" in last["quality"]["flags"]


def test_AC_EX_08_repeated_header_removed(tmp_path: Path) -> None:
    header = "॥ श्रीमद्भगवद्गीता ॥"
    pages: list[Any] = [[T(header, 40), *verse_lines(n, 200)] for n in range(1, 4)]
    units = extract(make_pdf(tmp_path / "h.pdf", pages), Config(), _no_ocr).units
    assert units
    assert all("श्रीमद्भगवद्गीता" not in u["text"] for u in units)


def test_AC_EX_09_low_ocr_confidence(tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "s.pdf", [Image(tuple(verse_lines(1, 100)))])
    engine = FakeEngine([("धर्मक्षेत्रे कुरुक्षेत्रे ।", 0.6), ("मामकाः सञ्जय ॥ १ ॥", 0.6)])
    unit = extract(pdf, Config(), lambda: engine).units[0]
    assert unit["quality"]["ocr_confidence"] == 0.6
    assert {"low_ocr_confidence", "needs_review"} <= set(unit["quality"]["flags"])


def test_AC_EX_12_vedic_accent_flagged_and_kept(tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "v.pdf", [[T("अ॒ग्निमी॑ळे पु॒रोहि॑तम् ।", 100), T("य॒ज्ञस्य॑ दे॒वमृ॒त्विज॑म् ॥ १ ॥", 120)]])
    unit = extract(pdf, Config(), _no_ocr).units[0]
    assert "॑" in unit["text"]
    assert {"vedic_accents_present", "needs_review"} <= set(unit["quality"]["flags"])


def test_AC_EX_13_only_scanned_pages_are_ocred(mixed_pdf: Path) -> None:
    engine = FakeEngine()
    units = extract(mixed_pdf, Config(), lambda: engine).units
    assert engine.calls == 2
    ocr_units = [u for u in units if u["source"]["page_start"] >= 6]
    assert ocr_units
    assert {u["extraction"]["tool"] for u in ocr_units} == {"tesseract"}


def test_AC_EX_14_dry_run(mixed_pdf: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli, "make_engine", lambda cfg: _no_ocr())
    result = CliRunner().invoke(cli.app, [str(mixed_pdf), "-o", str(tmp_path / "o"), "--dry-run"])
    assert result.exit_code == 0
    assert "2 pages need OCR" in result.output
    assert not (tmp_path / "o").exists()


def test_AC_EX_16_missing_tesseract_model(mixed_pdf: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        doctor, "check", lambda: doctor.DoctorResult(False, f"missing: san. Install with: {doctor.INSTALL_HINT}")
    )
    result = CliRunner().invoke(cli.app, [str(mixed_pdf), "-o", str(tmp_path / "o")])
    assert result.exit_code == 2
    assert doctor.INSTALL_HINT in result.output
    text_only = make_pdf(tmp_path / "t.pdf", [verse_lines(1, 100)])
    assert CliRunner().invoke(cli.app, [str(text_only), "-o", str(tmp_path / "o2")]).exit_code == 0


def test_AC_EX_17_heading_verses_colophon_and_stray_text(tmp_path: Path) -> None:
    page = [T("अर्जुनविषादयोगः", 60, x=None, size=18)]
    page += verse_lines(1, 120) + verse_lines(2, 180) + verse_lines(3, 240)
    page.append(T("इति श्रीमद्भगवद्गीतासु प्रथमोऽध्यायः", 300))
    units = extract(make_pdf(tmp_path / "c.pdf", [page]), Config(), _no_ocr).units
    assert _types(units) == ["heading", "verse", "verse", "verse", "heading"]

    stray = [T("यह एक साधारण वाक्य है", 100), *verse_lines(1, 160)]
    units = extract(make_pdf(tmp_path / "s.pdf", [stray]), Config(), _no_ocr).units
    assert _types(units) == ["other", "verse"]
    assert "needs_review" in units[0]["quality"]["flags"]
    assert "prose" not in _types(units)


# --- reference PDF (01_Chapter_Sanskrit.pdf, Sanskrit99) -----------------------------------------


@pytest.fixture(scope="module")
def ref_units() -> list[dict[str, Any]]:
    from tests.conftest import REFERENCE_PDF

    if not REFERENCE_PDF.exists():
        pytest.skip("reference PDF missing")
    return extract(REFERENCE_PDF, Config(), _no_ocr).units


def test_reference_pdf_all_47_verses_in_order(ref_units: list[dict[str, Any]]) -> None:
    verses = [u for u in ref_units if u["unit_type"] == "verse"]
    assert [v["verse_ref"]["normalized"] for v in verses] == [str(n) for n in range(1, 48)]
    assert {u["extraction"]["method"] for u in ref_units} == {"legacy_font_map"}
    assert all(u["quality"]["score"] == 1.0 for u in ref_units)
    assert _types(ref_units).count("heading") == 4  # invocation, chapter, title, colophon


def test_AC_EX_05_text_raw_is_engine_output(ref_units: list[dict[str, Any]], reference_pdf: Path) -> None:
    with PdfDocument(reference_pdf) as doc:
        raw_lines = {ln.text for p in doc.pages() for ln in p.lines}
    for u in ref_units:
        for raw in u["text_raw"].split("\n"):
            assert raw in raw_lines


def test_AC_EX_10_deterministic(reference_pdf: Path, tmp_path: Path) -> None:
    run_batch(reference_pdf, tmp_path / "a", Config(), _no_ocr)
    run_batch(reference_pdf, tmp_path / "b", Config(), _no_ocr)
    files = sorted(p.name for p in (tmp_path / "a").iterdir())
    assert files
    for name in files:
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()


def test_AC_EX_11_all_units_valid(ref_units: list[dict[str, Any]]) -> None:
    for u in ref_units:
        assert_valid_unit(u)


def test_AC_EX_15_offline(socket_disabled: None, reference_pdf: Path, tmp_path: Path) -> None:
    result = run_batch(reference_pdf, tmp_path, Config(), _no_ocr)
    assert not result.failed
    assert result.written


def test_AC_EX_18_speaker_units(ref_units: list[dict[str, Any]]) -> None:
    seq = [(u["unit_type"], (u["verse_ref"] or {}).get("normalized"), u["text"]) for u in ref_units]
    i = next(i for i, s in enumerate(seq) if s[1] == "1")
    assert seq[i - 1][0] == "speaker"
    assert seq[i - 1][2] == "धृतराष्ट्र उवाच -"
    v21 = next(u for u in ref_units if (u["verse_ref"] or {}).get("normalized") == "21")
    assert len(v21["lines"]) == 2
    assert "split_by_speaker" in v21["quality"]["flags"]
    after = ref_units[v21["seq"]]  # seq is 1-based, so this is the next unit
    assert (after["unit_type"], after["text"]) == ("speaker", "अर्जुन उवाच -")


# --- gold text (Q1b) -------------------------------------------------------------------------------


def _page_text(units: list[dict[str, Any]], page: int) -> str:
    return "\n".join(ln for u in units if u["source"]["page_start"] == page for ln in u["lines"])


def _cer(a: str, b: str) -> float:
    from rapidfuzz.distance import Levenshtein

    return float(Levenshtein.normalized_distance(" ".join(a.split()), " ".join(b.split())))


@pytest.mark.gold
def test_gold_mapping_matches_gold_text(ref_units: list[dict[str, Any]]) -> None:
    """Q9 measurement, mapping side: Sanskrit99 table vs. hand-checked gold text."""
    golds = gold_pages("01_Chapter_Sanskrit")
    if not golds:
        pytest.skip(f"no gold text yet in {GOLD_DIR} (Q1b)")
    for page, text in golds.items():
        assert _cer(_page_text(ref_units, page), text) == 0.0, f"page {page}"


@pytest.mark.ocr
@pytest.mark.gold
def test_AC_EX_04_ocr_cer(reference_pdf: Path, tmp_path: Path) -> None:
    """Q9 measurement, OCR side: render gold pages as scans, OCR them, CER ≤ 5 %."""
    golds = gold_pages("01_Chapter_Sanskrit")
    if not golds:
        pytest.skip(f"no gold text yet in {GOLD_DIR} (Q1b)")
    if not doctor.check().ok:
        pytest.skip("Tesseract with san+hin not installed")
    import pymupdf

    from sanskrit_extract.ocr.tesseract import TesseractEngine

    src = pymupdf.open(reference_pdf)
    scan = pymupdf.open()
    for page in sorted(golds):
        p = scan.new_page(width=src[page - 1].rect.width, height=src[page - 1].rect.height)
        p.insert_image(p.rect, stream=src[page - 1].get_pixmap(dpi=300).tobytes("png"))
    scan_path = tmp_path / "scan.pdf"
    scan.save(scan_path)
    units = extract(scan_path, Config(), lambda: TesseractEngine(cache_dir=None)).units
    report = {}
    for i, page in enumerate(sorted(golds), start=1):
        report[page] = _cer(_page_text(units, i), golds[page])
    (tmp_path / "cer.json").write_text(json.dumps(report))
    assert all(v <= 0.05 for v in report.values()), report


def test_AC_EX_19_coverage_nothing_lost_silently() -> None:
    from tests.conftest import REFERENCE_PDF

    if not REFERENCE_PDF.exists():
        pytest.skip("reference PDF missing")
    report = extract(REFERENCE_PDF, Config(), _no_ocr).report
    cov = report["coverage"]
    assert cov["unaccounted"] == 0
    assert cov["lines_read"] == cov["lines_in_units"] + cov["lines_removed"]
    assert len(report["removed_lines"]) == cov["lines_removed"] == 12  # 2 header lines + page number, × 4 pages
    assert {r["reason"] for r in report["removed_lines"]} == {"header_footer", "page_number"}
    assert all(r["page"] and r["text"] for r in report["removed_lines"])


class _EchoEngine:
    """Verification engine that 'reads' a fixed text for every line."""

    name = "tesseract"

    def __init__(self, text: str) -> None:
        self.text = text
        self.calls = 0

    def version(self) -> str:
        return "fake"

    def ocr(self, png: bytes, dpi: int) -> list[Any]:
        from sanskrit_extract.ocr.base import OcrLine

        self.calls += 1
        return [OcrLine(self.text, 0.9, (0.0, 0.0, 1.0, 1.0))]


def _verify_cfg() -> Config:
    cfg = Config()
    cfg.verify.enabled = True
    return cfg


def test_AC_EX_20_ocr_cross_check(tmp_path: Path) -> None:
    line = "मामकाः पाण्डवाश्चैव किमकुर्वत सञ्जय ॥ १ ॥"
    pdf = make_pdf(tmp_path / "v.pdf", [[T(line, 100)]])
    same = extract(pdf, _verify_cfg(), _no_ocr, verify_engine_factory=lambda: _EchoEngine(line))
    assert "ocr_disagreement" not in same.units[0]["quality"]["flags"]
    assert same.report["verification"]["units_checked"] == 1
    assert same.report["verification"]["units_disagreeing"] == 0

    other = extract(pdf, _verify_cfg(), _no_ocr, verify_engine_factory=lambda: _EchoEngine("कखगघ ॥ १ ॥"))
    assert {"ocr_disagreement", "needs_review"} <= set(other.units[0]["quality"]["flags"])
    (dis,) = other.report["verification"]["disagreements"]
    assert dis["unit_id"] == other.units[0]["unit_id"]
    assert dis["cer"] > 0.4


def test_AC_EX_21_verification_never_changes_text(tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "v.pdf", [verse_lines(1, 100)])
    plain = extract(pdf, Config(), _no_ocr).units
    checked = extract(pdf, _verify_cfg(), _no_ocr, verify_engine_factory=lambda: _EchoEngine("कखग")).units
    for a, b in zip(plain, checked, strict=True):
        assert (a["text"], a["lines"], a["text_raw"]) == (b["text"], b["lines"], b["text_raw"])
    assert plain[0]["quality"]["flags"] != checked[0]["quality"]["flags"]
    assert Config().verify.enabled is False  # off unless asked for


def test_AC_EX_22_broken_line_on_legacy_page_is_ocred_alone(tmp_path: Path) -> None:
    import pymupdf

    from tests.conftest import REFERENCE_PDF
    from tests.fixtures.factory import FONT_FILE, require_font

    if not REFERENCE_PDF.exists():
        pytest.skip("reference PDF missing")
    require_font()
    doc = pymupdf.open()
    doc.insert_pdf(pymupdf.open(REFERENCE_PDF), from_page=0, to_page=0)
    page = doc[0]
    page.insert_font(fontname="dv", fontfile=str(FONT_FILE))
    page.insert_text((400, 580), "ॐ तत्सिभभत िवजय िकम ाम", fontname="dv", fontsize=12)  # broken text layer
    pdf = tmp_path / "mixed.pdf"
    doc.save(pdf)
    engine = _EchoEngine("ॐ तत्सदिति")
    units = extract(pdf, Config(), _no_ocr, verify_engine_factory=lambda: engine).units
    assert engine.calls == 1
    methods = {u["extraction"]["method"] for u in units}
    assert methods == {"legacy_font_map", "ocr"}
    assert [v["verse_ref"]["normalized"] for v in units if v["unit_type"] == "verse"] == [str(n) for n in range(1, 12)]
    assert any(u["text"] == "ॐ तत्सदिति" and u["extraction"]["method"] == "ocr" for u in units)


def test_AC_EX_23_centred_verses_titles_and_toc(tmp_path: Path) -> None:
    verse = [
        "ॐ पार्थाय प्रतिबोधितां भगवता नारायणेन स्वयं",
        "व्यासेन ग्रथितां पुराणमुनिना मध्ये महाभारतम् ।",
        "अद्वैतामृतवर्षिणीं भगवतीम् अष्टादशाध्यायिनीं",
        "अम्ब त्वाम् अनुसन्दधामि भगवद्गीते भवद्वेषिणीम् ॥",
    ]
    page = [T("गीताध्यानश्लोकाः", 80, x=None), *[T(t, 120 + 22 * i, x=None) for i, t in enumerate(verse)]]
    page.append(T("1. अर्जुनविषादयोगः ............................ 1", 260, x=60))
    units = extract(make_pdf(tmp_path / "c.pdf", [page]), Config(), _no_ocr).units
    assert _types(units) == ["heading", "verse", "heading"]
    assert units[1]["lines"] == verse
    assert "unnumbered_verse" in units[1]["quality"]["flags"]


def test_AC_EX_24_iti_verse_colophon_span_footnote_and_title(tmp_path: Path) -> None:
    page = [
        T("गीता आरति", 60),
        T("This shloka is not found in all manuscripts", 110, latin=True),
        T("न मां कर्माणि लिम्पन्ति न मे कर्मफले स्पृहा ।", 160),
        T("इति मां योऽभिजानाति कर्मभिर्न स बध्यते ॥ १४ ॥", 180),
        T("॥ ॐ तत्सदिति श्रीमद्भगवद्गीतासु उपनिषत्सु ब्रह्मविद्यायां", 240),
        T("योगशास्त्रे श्रीकृष्णार्जुनसंवादे कर्मयोगो नाम तृतीयोऽध्यायः ॥", 260),
    ]
    units = extract(make_pdf(tmp_path / "i.pdf", [page]), Config(), _no_ocr).units
    assert _types(units) == ["heading", "other", "verse", "heading"]
    assert units[2]["verse_ref"]["normalized"] == "14"
    assert len(units[2]["lines"]) == 2
    assert len(units[3]["lines"]) == 2
    assert units[1]["script"] == "latin"


# --- FR-EX-08 headers/footers, FR-EX-21 page selection ----------------------------------------------------------

_DEVA = str.maketrans("0123456789", "०१२३४५६७८९")


def _texts(units: list[dict[str, Any]]) -> str:
    return "\n".join(u["text"] for u in units)


def test_AC_EX_25_alternating_headers_removed(tmp_path: Path) -> None:
    pages: list[Any] = []
    for n in range(1, 9):  # page 1..8; chapter changes at page 5
        chapter = "१ ॥ अर्जुनविषादयोगः ॥" if n < 5 else "२ ॥ साङ्ख्ययोगः ॥"
        head = "॥ श्रीमद्भगवद्गीता ॥" if n % 2 == 0 else chapter
        pages.append([T(head, 40), *verse_lines(n, 200)])
    units = extract(make_pdf(tmp_path / "alt.pdf", pages), Config(), _no_ocr).units
    text = _texts(units)
    assert "श्रीमद्भगवद्गीता" not in text and "अर्जुनविषादयोगः" not in text and "साङ्ख्ययोगः" not in text
    assert sum(1 for u in units if u["unit_type"] == "verse") == 8


def test_AC_EX_25_separator_rules_define_margins(tmp_path: Path) -> None:
    pages: list[Any] = []
    for n in range(1, 4):
        num = str(n).translate(_DEVA)
        pages.append(
            [
                T(f"अध्यायः {num} शीर्षकम्", 30, size=14),  # differs on every page: only the rule finds it
                Rule(45),
                T("॥ ॐ श्री परमात्मने नमः ॥", 62, size=14),  # body text just below the rule, inside the zone
                *verse_lines(n, 200),
                Rule(800),
                T(f"टिप्पणी {num} पृष्ठम्", 818, size=14),
            ]
        )
    doc = extract(make_pdf(tmp_path / "rules.pdf", pages), Config(), _no_ocr)
    text = _texts(doc.units)
    assert "शीर्षकम्" not in text and "पृष्ठम्" not in text
    assert text.count("परमात्मने") == 3
    reasons = [r["reason"] for r in doc.report["removed_lines"]]
    assert reasons.count("header_footer") == 6
    assert doc.report["coverage"]["unaccounted"] == 0


def test_AC_EX_25_small_font_margin_line_removed(tmp_path: Path) -> None:
    pages: list[Any] = [
        [T("गीता सारः", 30, size=8), *verse_lines(1, 200)],
        [T("गीता सारः", 30, size=8), *verse_lines(2, 200)],
        [T("॥ ॐ श्री परमात्मने नमः ॥", 30, size=14), *verse_lines(3, 200)],
        [*verse_lines(4, 200)],
        [*verse_lines(5, 200)],
    ]
    text = _texts(extract(make_pdf(tmp_path / "small.pdf", pages), Config(), _no_ocr).units)
    assert "सारः" not in text  # small font, on 2 of 5 pages
    assert "परमात्मने" in text  # body size, once


@pytest.fixture
def four_pages(tmp_path: Path) -> Path:
    return make_pdf(tmp_path / "four.pdf", [verse_lines(n, 200) for n in range(1, 5)])


def _verse_numbers(units: list[dict[str, Any]]) -> list[str]:
    return [u["verse_ref"]["normalized"] for u in units if u["unit_type"] == "verse"]


def test_AC_EX_26_page_selection(four_pages: Path, tmp_path: Path) -> None:
    from sanskrit_extract.pages import PageSelection

    doc = extract(four_pages, Config(), _no_ocr, PageSelection.parse("2-3"))
    assert _verse_numbers(doc.units) == ["2", "3"] and doc.report["pages_selected"] == [2, 3]
    assert _verse_numbers(extract(four_pages, Config(), _no_ocr, PageSelection.parse("3-")).units) == ["3", "4"]
    doc = extract(four_pages, Config(), _no_ocr, PageSelection.parse("3-9"))
    assert _verse_numbers(doc.units) == ["3", "4"] and doc.report["pages_missing"] == [5, 6, 7, 8, 9]
    assert extract(four_pages, Config(), _no_ocr).report["pages_selected"] is None

    runner = CliRunner()
    r = runner.invoke(cli.app, [str(four_pages), "-o", str(tmp_path / "o1"), "--pages", "3-9"])
    assert r.exit_code == 0 and "pages 5-9 skipped" in r.stdout
    r = runner.invoke(cli.app, [str(four_pages), "-o", str(tmp_path / "o2"), "--pages", "7-9"])
    assert r.exit_code == 1
    for bad in ("0", "5-2", "x"):
        assert runner.invoke(cli.app, [str(four_pages), "-o", str(tmp_path / "o3"), "--pages", bad]).exit_code == 2


BOOK = Path(__file__).resolve().parents[3] / "input" / "pdf" / "SrimadBhagawadGeeta_Sanskrit.pdf"


@pytest.mark.skipif(not BOOK.exists(), reason="reference book not present")
def test_AC_EX_27_reference_book_running_headers(tmp_path: Path) -> None:
    from sanskrit_extract.pages import PageSelection

    doc = extract(BOOK, Config(), _no_ocr, PageSelection.parse("9-24"))  # chapter 1 and part of chapter 2
    texts = [u["text"] for u in doc.units]
    assert not any(t.strip() == "॥ श्रीमद्भगवद्गीता ॥" for t in texts)
    assert not any(t.endswith("॥ अर्जुनविषादयोगः ॥") or t.endswith("॥ साङ्ख्ययोगः ॥") for t in texts)
    assert sum(1 for t in texts if "परमात्मने नमः" in t) == 2  # chapters 1 and 2 open with it
    assert doc.report["coverage"]["unaccounted"] == 0


@pytest.mark.skipif(not BOOK.exists(), reason="reference book not present")
def test_AC_EX_28_reference_book_chapter_titles_not_in_verse_1() -> None:
    from sanskrit_extract.pages import PageSelection

    openings = "9,17,30,37,44,49,57,62,67,73,80,94,98,104,109,113,117,122"  # first page of chapters 1-18
    doc = extract(BOOK, Config(), _no_ocr, PageSelection.parse(openings))
    firsts = [u for u in doc.units if u["unit_type"] == "verse" and (u.get("verse_ref") or {}).get("normalized") == "1"]
    assert len(firsts) == 18
    for u in firsts:
        assert not any(ln.rstrip().endswith("योगः") for ln in u["lines"]), u["lines"][0]
    headings = {u["text"].strip() for u in doc.units if u["unit_type"] == "heading"}
    assert {"अर्जुनविषादयोगः", "साङ्ख्ययोगः", "कर्मयोगः", "मोक्षसन्न्यासयोगः"} <= headings
