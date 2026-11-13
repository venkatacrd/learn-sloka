# 001 – PDF Extractor: Tasks

Rules: do tasks in order; each task = failing test(s) first, then code; a task is done when its tests pass,
`ruff` + `mypy` pass, and no other test broke. `[P]` = can run in parallel with the previous task.

**Status (2026-11-08):** EX-T01–T16 implemented in [pdf-extractor/](../../pdf-extractor/); 76 tests pass.
Open: AC-EX-04 (OCR CER) and the gold-text comparison wait for Tesseract (`brew install tesseract tesseract-lang`)
and the gold files (Q1b).

| ID | Task | Satisfies | Tests to write first | Depends |
|----|------|-----------|----------------------|---------|
| EX-T01 | Scaffold `pdf-extractor/` package (pyproject, src layout, ruff, mypy, pytest, typer entry point `sanskrit-extract --version`) | constitution 9, 11 | `test_cli_version` | – |
| EX-T02 | Contract test harness: load `extracted-unit.schema.json`, helper `assert_valid_unit()` | NFR-EX-01 | `test_schema_loads`, invalid sample rejected | T01 |
| EX-T03 | Fixture factory: generate Unicode-text PDFs from gold strings; use reference PDF `01_Chapter_Sanskrit.pdf` (Q1a) + gold `.txt` (Q1b) | – | `test_fixture_roundtrip_text` | T01 |
| EX-T04 | `syllables.py`: Devanagari ratio + syllable validity | FR-EX-02, 12 | valid/invalid cluster tables | T01 [P] |
| EX-T05 | `normalize.py` rules, each switchable | FR-EX-06, 07, 13 | per-rule tests; hypothesis idempotence; AC-EX-12 | T04 |
| EX-T06 | `pdf_reader.py` + `page_classifier.py` | FR-EX-02, 03 | AC-EX-02, AC-EX-03 (classification part) | T03, T04 |
| EX-T07 | `ocr/base.py` protocol + `ocr/tesseract.py` | FR-EX-04, NFR-EX-05 | fake engine unit test; AC-EX-04 (`@ocr`) | T06 |
| EX-T08 | `layout.py`: header/footer/page-number removal, line order | FR-EX-08 | AC-EX-08 | T06 |
| EX-T09 | `segmenter.py`: units, verse refs, cross-page join, profiles | FR-EX-09, 10, 11, 16 | AC-EX-06, AC-EX-07, AC-EX-17, AC-EX-18, verse-ref table test | T05, T08 |
| EX-T10 | `quality.py`: score + flags | FR-EX-12, 13 | AC-EX-09, AC-EX-12 | T07, T09 |
| EX-T11 | `legacy_fonts/` mapping hook (interface + Sanskrit99 table – reference PDF uses it, Q9) | FR-EX-05 | mapping unit test; i-matra reordering test; mapping vs. OCR error rate on gold pages (Q1b) | T06 [P] |
| EX-T12 | `writer.py` + `pipeline.py`: JSONL + report, deterministic | FR-EX-14, NFR-EX-02 | AC-EX-05, AC-EX-10, AC-EX-11 | T10 |
| EX-T13 | `cli.py`: full options, batch, exit codes | FR-EX-01, 15 | AC-EX-01 | T12 |
| EX-T14 | Performance check on a 200-page sample | NFR-EX-03, 04 | `@slow` benchmark test | T13 |
| EX-T15 | README for the package (usage, install tesseract + language models, config reference) | – | – | T16 |
| EX-T17 | Coverage audit in report | FR-EX-19 | AC-EX-19 | T12 |
| EX-T18 | OCR cross-check of non-OCR units (`verify.py`), report block, `--verify-ocr` | FR-EX-20 | AC-EX-20, AC-EX-21 | T16, T17 |
| EX-T19 | Per-line OCR on legacy pages; heading rule by width; TOC lines; table 1.1.0 (full Gita PDF) | FR-EX-02, 05, 09 | AC-EX-22, AC-EX-23 | T18 |
| EX-T20 | Colophon spans, `इति` verses, Latin lines, lone titles; reph before `ं`; stricter syllable check; OCR check on Devanagari only | FR-EX-05, 09, 12, 20 | AC-EX-24 | T19 |
| EX-T21 | Header/footer detection: separator rules, odd/even repeats, small-font margin repeats | FR-EX-08 | AC-EX-25, AC-EX-27 | T20 |
| EX-T22 | Page selection: open-ended ranges, missing pages reported, `pages_selected` | FR-EX-21 | AC-EX-26 | T21 |
| EX-T23 | Heading centring against the odd/even text frame (titles on odd pages of the reference book were read into verse 1) | FR-EX-09 | AC-EX-28 | T19 |
| EX-T24 | Speaker lines with `उवाच` joined by sandhi (`भगवानुवाच`) | FR-EX-09 | AC-EX-29 | T23 |
| EX-T16 | `ocr/doctor.py` install check, `ocr/preprocess.py`, OCR cache, `--dry-run`; offline guard test | FR-EX-04, 17, 18, NFR-EX-05 | AC-EX-13, 14, 15, 16 | T07, T13 |

Definition of done for feature 001: all AC-EX-xx tests green, traceability table below complete.

## Traceability

| Requirement | Tasks | Acceptance |
|-------------|-------|-----------|
| FR-EX-01 | T13 | AC-EX-01 |
| FR-EX-02 | T04, T06 | AC-EX-02, 03 |
| FR-EX-03 | T06 | AC-EX-02 |
| FR-EX-04 | T07, T16 | AC-EX-03, 04, 13 |
| FR-EX-05 | T11 | unit test |
| FR-EX-06 | T05, T12 | AC-EX-05 |
| FR-EX-07 | T05 | AC-EX-02 |
| FR-EX-08 | T08, T21 | AC-EX-08, 25, 27 |
| FR-EX-21 | T22 | AC-EX-26 |
| FR-EX-09/10 | T09 | AC-EX-06, 17, 18 |
| FR-EX-11 | T09 | AC-EX-07 |
| FR-EX-12 | T10 | AC-EX-09 |
| FR-EX-13 | T05, T10 | AC-EX-12 |
| FR-EX-14/15 | T12, T13 | AC-EX-01 |
| FR-EX-16 | T09 | profile test |
| NFR-EX-01 | T02, T12 | AC-EX-11 |
| NFR-EX-02 | T12 | AC-EX-10 |
| NFR-EX-03/04 | T14 | benchmark |
| NFR-EX-05 | T07, T16 | fake-engine test, AC-EX-15 |
| FR-EX-17 | T16 | AC-EX-16 |
| FR-EX-18 | T16 | AC-EX-14 |
