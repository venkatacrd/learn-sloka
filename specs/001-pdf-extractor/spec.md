# 001 – PDF Extractor: Specification

Status: Draft · Contract: [extracted-unit 1.2.0](../contracts/extracted-unit.schema.json)

## Purpose

Read Sanskrit PDFs and output the Devanagari text **as it is in the source**, segmented into verses and other
units, as JSONL that the transliterator (002) consumes. The extractor never romanizes.

## Users / consumers

- Operator running a batch over a folder of PDFs.
- Project 002 (reads the JSONL).
- A human reviewer checking flagged pages.

## User stories

- **US-1** As an operator, I point the tool at a PDF or folder and get one JSONL file per PDF.
- **US-2** As an operator, I get correct Devanagari even when the PDF is scanned or has a broken text layer.
- **US-3** As a reviewer, I get a report of pages/units that need checking, with reasons.
- **US-4** As the transliterator, I receive one record per verse with its verse number and source page.

## Functional requirements

| ID | Requirement |
|----|-------------|
| FR-EX-01 | Accept a single PDF path or a directory (recursive, `*.pdf`). Skip and report unreadable/encrypted files without stopping the batch. |
| FR-EX-02 | Classify **each page** as `text_layer_ok`, `text_layer_broken`, `legacy_font`, or `image_only` (see analysis §2). A page that uses a configured legacy font is `legacy_font`. On such a page, lines in other fonts are routed **per line**: a line whose own text layer is broken (syllable validity below the threshold) is OCR'd on its own; the legacy-font lines are still decoded by their table. |
| FR-EX-03 | For `text_layer_ok` pages, extract text from the text layer preserving reading order and line breaks. |
| FR-EX-04 | For `image_only` and `text_layer_broken` pages, render at ≥300 DPI and OCR them locally with **Tesseract** `san+hin` (Q6: offline only); record per-line confidence. Pages with a good text layer are never OCR'd (faster, and avoids OCR errors). |
| FR-EX-05 | For `legacy_font` pages, apply a font mapping table if one is configured for that font; otherwise OCR. |
| FR-EX-06 | Keep the untouched extracted string in `text_raw`. |
| FR-EX-07 | Produce `text` by: NFC normalization; removal of soft hyphens and control characters; collapsing runs of spaces; standardizing danda look-alikes (`|`, `||`, `I`) to `।`/`॥` **only** when adjacent to Devanagari; removing ZWJ/ZWNJ only where they do not change the rendered conjunct. Danda spacing: exactly one space before `।` / `॥`, and verse numbers between double dandas written `॥ १ ॥` (spacing only; no character is added or removed). Each rule individually testable and switchable in config. |
| FR-EX-08 | Remove running page headers, footers and page numbers. A line in the top/bottom `header_zone` is removed when any of these holds: (a) it is a bare number (page number); (b) its text (digits ignored) repeats in the zone on ≥ 50 % of pages, or on ≥ 50 % of the odd pages or of the even pages (books alternate left/right headers, e.g. `॥ श्रीमद्भगवद्गीता ॥` / `१ ॥ अर्जुनविषादयोगः ॥`); (c) it lies entirely above a horizontal separator rule in the top `rule_zone` or below one in the bottom `rule_zone`, where a rule at that height appears on ≥ 50 % of the read pages; (d) its font is ≤ `small_font_ratio` (0.8) × the body text size and its text repeats in the zone on ≥ 2 pages. Every removed line is listed in the report (reason `header_footer` or `page_number`), never dropped silently. |
| FR-EX-09 | Segment text into units. Input is expected to be slokas only (Q2). A `verse` ends at `॥` (with optional verse number before/after it); `।` marks half-verse and does not end a unit. Narrow lines (≤ 38 % of the page width, configurable) without `।` that are centred or in a different font size, colophons and table-of-contents entries (lines with leader dots `....`) become `heading`. A colophon starts with `इति`/`ॐ तत्सदिति` (optionally after `॥`) or is a line ending in `… अध्यायः ॥`; it may span several lines and ends at the line ending in `॥`; a line with a verse number or a half-verse `।` is never a colophon, and a colophon span that closes with a verse number is a verse (verses may begin with `इति` or `ॐ तत्सदिति`, e.g. Gita 4.14, 13.18, 17.23). A line ending in `॥` always closes an open verse. A line that is not Devanagari (e.g. an English footnote) is its own `other` unit and never joins a verse. A lone short line (≤ 3 words, no danda) that does not belong to a verse is a `heading`. A line that ends in `उवाच` (optionally followed by `-`, `:` or `।`) becomes its own `speaker` unit, also when `उवाच` is joined to the name by sandhi and so starts with the vowel sign `ु` (`श्री भगवानुवाच -`, `श्रीविष्णुरुवाच`). When a speaker line sits inside a verse (e.g. Gita 1.21), the verse stays **one** `verse` unit (its `lines` exclude the speaker line) and gets flag `split_by_speaker`; the `speaker` unit follows it directly in `seq`. Lines separated from a verse by an empty gap taller than 0.75 × line height (configurable) are not part of that verse. Anything else becomes `other` and is flagged `needs_review` (signals the "slokas only" assumption broke). `prose` is not produced in Phase 1 (P2-02). "Centred" is measured against the **text frame**, worked out separately for odd and even pages (books mirror their margins): from the most common left edge to the 95th-percentile right edge of the wide lines (> 38 % of the page width) on pages of that parity; with fewer than 10 such lines the page centre is used. |
| FR-EX-10 | Parse verse numbers in Devanagari or ASCII digits (`॥ १ ॥`, `॥ २-४७ ॥`, `॥२.४७॥`, `1.47`) into `verse_ref.normalized` (`2.47`). |
| FR-EX-11 | Join a verse that continues across a page break into one unit with `page_start` < `page_end` and flag `crosses_page`. |
| FR-EX-12 | Compute a quality score 0–1 per unit from: Devanagari ratio, syllable-validity ratio, OCR confidence (if OCR). Add flags per the contract enum. Flag `needs_review` when score < configurable threshold (default 0.85). |
| FR-EX-13 | Phase 1 (Q3: no accents expected): detect Vedic accent marks (U+0951–0954, U+1CD0–1CFF) and flag the unit `vedic_accents_present` + `needs_review`; keep the marks unchanged in `text`. Full accent support is Phase 2 (P2-01). |
| FR-EX-14 | Write `<out>/<doc_id>.jsonl` (one unit per line, in reading order) and `<out>/<doc_id>.report.json` (page classes, counts, flagged units). |
| FR-EX-15 | CLI: `sanskrit-extract <input> -o <outdir> [--config file.toml] [--force-ocr] [--pages 1-10|10-] [--dpi N] [--profile name] [--dry-run] [--verify-ocr]`. Exit code 0 = success, 1 = some files failed, 2 = bad usage. |
| FR-EX-16 | Segmentation "profiles" (TOML) let a book override verse-end markers, number patterns, and header/footer zones. |
| FR-EX-17 | Check at startup that Tesseract and the `san` and `hin` language models are installed; if missing, exit with code 2 and print the install command (`brew install tesseract tesseract-lang`). Skip this check when no page needs OCR. |
| FR-EX-19 | **Coverage audit (no silent loss).** Every non-blank line read from a page (text layer, legacy map or OCR) is accounted for: it is either in a unit or listed in the report under `removed_lines` with page, text and reason (`header_footer`, `page_number`, `empty_after_cleanup`). The report's `coverage` block gives `lines_read`, `lines_in_units`, `lines_removed`, `unaccounted`; `unaccounted` must be 0. |
| FR-EX-20 | **Automatic OCR cross-check** (`--verify-ocr`, Q11). For every Devanagari unit not already read by OCR, OCR each of its printed lines from the rendered page (300 DPI, single-line mode) and compare only the Devanagari letters and signs of both readings (spacing, punctuation, digits and leader dots are ignored). An empty OCR result counts as *not checked* (reported), not as a disagreement. Character error rate (CER) above a configurable threshold (default 0.40; measured on the reference PDF: correct text vs. Tesseract gives mean CER ≈ 0.10, max ≈ 0.27, so the check catches gross failures such as a wrong font table or garbled page, not single-character errors) adds flags `ocr_disagreement` + `needs_review`. Verification never changes `text`. The report's `verification` block lists units checked, units disagreeing, mean CER, and for each disagreeing unit its CER and the OCR text. Requires Tesseract (FR-EX-17 check applies). |
| FR-EX-21 | `--pages` selects pages: `5`, `1-10`, `1,3-4`, or open-ended `10-` (to the last page). Selected pages that the document does not have are reported (`pages_missing` in the report and a note on the console); a PDF with none of the selected pages fails (exit 1). The report lists `pages_selected`. |
| FR-EX-18 | `--dry-run` reports each page's class and how many pages would need OCR, without running OCR or writing units. |

## Non-functional requirements

| ID | Requirement |
|----|-------------|
| NFR-EX-01 | Every output line validates against `extracted-unit.schema.json`. |
| NFR-EX-02 | Deterministic: same input+config+version ⇒ byte-identical output. |
| NFR-EX-03 | Text-layer path: ≥ 20 pages/s; OCR path: ≤ 10 s/page on an M-series Mac at 300 DPI. |
| NFR-EX-04 | Memory bounded per page (stream pages, do not load whole book of images). |
| NFR-EX-05 | Fully offline: no network calls at runtime; no cloud SDKs among the dependencies. OCR sits behind an `OcrEngine` interface so another *offline* engine could be added later. |
| NFR-EX-06 | Structured logs (JSON) with doc_id and page number. |

## Acceptance criteria

| ID | Given / When / Then | Covers |
|----|---------------------|--------|
| AC-EX-01 | Given a folder with 2 valid PDFs and 1 corrupt file, when run, then 2 JSONL + 2 reports are written, the corrupt file is listed in the summary, exit code is 1. | FR-EX-01, 14, 15 |
| AC-EX-02 | Given a generated Unicode-font PDF of the 1st Gita verse, page is classified `text_layer_ok` and `text` equals the gold string exactly. | FR-EX-02, 03, 07 |
| AC-EX-03 | Given a PDF whose text layer has reordered `ि` matras, page is classified `text_layer_broken` and extraction method is `ocr`. | FR-EX-02, 04 |
| AC-EX-04 | Given a scanned (image-only) page from the gold set, OCR output has character error rate ≤ 5 % vs. gold. | FR-EX-04 |
| AC-EX-05 | `text_raw` of every unit equals the substring the engine returned, byte for byte. | FR-EX-06 |
| AC-EX-06 | Given `धर्मक्षेत्रे ... युयुत्सवः । मामकाः ... सञ्जय ॥ १-१ ॥`, one `verse` unit is produced with `verse_ref.normalized = "1.1"` and 2 `lines`. | FR-EX-09, 10 |
| AC-EX-07 | Given a verse split across pages 4–5, one unit with `page_start=4`, `page_end=5`, flag `crosses_page`. | FR-EX-11 |
| AC-EX-08 | Given a document with identical header on every page, header text appears in no unit. | FR-EX-08 |
| AC-EX-09 | A unit with OCR confidence 0.6 is flagged `low_ocr_confidence` and `needs_review`. | FR-EX-12 |
| AC-EX-10 | Running twice produces identical files (hash compare). | NFR-EX-02 |
| AC-EX-11 | All units in all gold outputs validate against the schema. | NFR-EX-01 |
| AC-EX-12 | Text containing U+0951 is flagged `vedic_accents_present` and `needs_review`, and the mark is kept in `text`. | FR-EX-13 |
| AC-EX-17 | Given a page with a chapter heading, 3 verses and a colophon `इति प्रथमोऽध्यायः`, output is: 1 `heading`, 3 `verse`, 1 `heading`, and no `prose`. A stray paragraph of non-verse text becomes `other` with `needs_review`. | FR-EX-09 |
| AC-EX-18 | Given `धृतराष्ट्र उवाच -` followed by verse 1, output is 1 `speaker` unit then 1 `verse`. Given Gita 1.21 with `अर्जुन उवाच -` between its two halves, output is 1 `verse` (`verse_ref` `21`, 2 `lines`, flag `split_by_speaker`) followed by 1 `speaker`. | FR-EX-09 |
| AC-EX-19 | For the reference PDF, `coverage.unaccounted = 0`, `lines_read = lines_in_units + lines_removed`, and every removed line is listed with page, text and reason. | FR-EX-19 |
| AC-EX-20 | With `--verify-ocr` and an OCR engine that returns the same text, no unit is flagged; with an engine that returns different text, the unit gets `ocr_disagreement` + `needs_review` and is listed in `verification` with its CER. | FR-EX-20 |
| AC-EX-21 | `text`, `lines` and `text_raw` are identical with and without `--verify-ocr`. | FR-EX-20 |
| AC-EX-22 | A page with Sanskrit99 verses and a line in another font whose text layer is broken: the verses are `legacy_font_map`, only the broken line is OCR'd (one OCR call). | FR-EX-02 |
| AC-EX-23 | Centred 4-line verses ending in `॥` (no number) are one `verse` each (flag `unnumbered_verse`), not headings; a narrow centred title stays a `heading`; a line with leader dots is a `heading`. | FR-EX-09 |
| AC-EX-24 | A verse starting with `इति` and numbered `॥ १४ ॥` is a `verse`; a two-line colophon `॥ ॐ तत्सदिति … / … अध्यायः ॥` is one `heading`; an English footnote line before a verse is a separate `other` unit; a lone title `गीता आरति` is a `heading`. | FR-EX-09 |
| AC-EX-25 | Pages with alternating headers (title on even pages, chapter name on odd pages, each repeated on < 50 % of all pages) → no header text in any unit. Pages with a header line above a separator rule that differs on every page, and a footer below a bottom rule → no header/footer text in any unit; the first body line just below the rule is kept. A small-font margin line repeated on 2 pages is removed; a normal-size first line in the zone (e.g. `॥ ॐ श्री परमात्मने नमः ॥` on a chapter's first page) is kept. | FR-EX-08 |
| AC-EX-26 | `--pages 2-3` on a 4-page PDF reads only pages 2–3 (`pages_selected = [2, 3]`); `--pages 3-` reads 3–4; `--pages 3-9` reads 3–4 and reports `pages_missing = [5..9]`; `--pages 7-9` → that file fails, exit 1; `--pages 0` or `5-2` → exit 2. | FR-EX-21 |
| AC-EX-27 | *(reference book, skipped if absent)* `SrimadBhagawadGeeta_Sanskrit.pdf`: no unit contains the running headers `॥ श्रीमद्भगवद्गीता ॥` or `<n> ॥ <chapter> ॥`, and each chapter's opening `॥ ॐ श्री परमात्मने नमः ॥` is still extracted. | FR-EX-08 |
| AC-EX-28 | Odd pages with text frame x 68–380 and even pages with x 18–330 on a 396-wide page: a chapter title centred in the frame (odd: x 188–264, even: x 140–210) directly above `सञ्जय उवाच -` and verse 1 is a `heading`, followed by the `speaker` unit and the `verse` (title not inside the verse); with fewer than 10 wide lines the page centre is used. *(reference book)* `SrimadBhagawadGeeta_Sanskrit.pdf`: the first verse unit of each of the 18 chapters contains no chapter-name line. | FR-EX-09 |
| AC-EX-29 | `श्री भगवानुवाच -` and `श्रीभगवानुवाच` before a verse → a `speaker` unit, then the `verse` (not inside it); `अर्जुन उवाच -` still a `speaker`. | FR-EX-09 |
| AC-EX-13 | Given a mixed PDF (5 text-layer pages, 2 scanned), OCR is called exactly 2 times and those units have `extraction.tool = "tesseract"`. | FR-EX-04 |
| AC-EX-14 | `--dry-run` on that PDF prints "2 pages need OCR" and makes zero OCR calls. | FR-EX-18 |
| AC-EX-15 | With network sockets blocked (`pytest-socket`), the full gold-set run succeeds. | NFR-EX-05 |
| AC-EX-16 | With Tesseract's `san` model missing (simulated), a scanned PDF exits with code 2 and the install command; a text-layer-only PDF still succeeds. | FR-EX-17 |

## Out of scope

Phase 2 backlog items (Vedic accents, commentary/translation text – see open-questions.md); romanization; translation; embeddings / vector stores; editing PDFs; non-Devanagari Indic scripts (Telugu, Grantha…) – possible later via the same OCR interface.
