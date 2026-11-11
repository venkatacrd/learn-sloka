# 001 – PDF Extractor: Technical Plan

Implements [spec.md](spec.md).

## Stack

| Concern | Choice | Why |
|---------|--------|-----|
| PDF parsing & rendering | **PyMuPDF** (`pymupdf`) | Fast, gives text with font names + positions (`get_text("dict")`), renders pages to images |
| OCR (offline only) | **Tesseract 5** via `pytesseract`, langs `san+hin`, with image preprocessing (grayscale, binarize, deskew) via `opencv-python-headless` | Free, offline. System dependency: `brew install tesseract tesseract-lang` |
| Unicode / syllables | stdlib `unicodedata` + own syllable regex | No heavy deps; rules are small and testable |
| Config | TOML (`tomllib`) + `pydantic` models | Validated config, profiles |
| Schema validation | `jsonschema` | Contract tests |
| CLI | `typer` | Thin layer |
| Tests | `pytest`, `hypothesis` (normalizer properties), `reportlab` or PyMuPDF to generate fixture PDFs | Fixtures are generated, not hand-made |

## Layout

```
pdf-extractor/
  pyproject.toml
  src/sanskrit_extract/
    cli.py               # typer app, arg parsing only           (FR-EX-15)
    config.py            # pydantic Config, profile loading     (FR-EX-16)
    pipeline.py          # orchestrates per-document flow
    pdf_reader.py        # PyMuPDF wrapper: pages, spans, fonts, render
    page_classifier.py   # text_layer_ok | broken | legacy | image (FR-EX-02)
    syllables.py         # Devanagari syllable validity + ratios
    ocr/
      base.py            # OcrEngine protocol: ocr(image) -> lines+conf
      tesseract.py       #                                       (FR-EX-04)
      preprocess.py      # binarize, deskew before OCR
      doctor.py          # checks tesseract + san/hin installed  (FR-EX-17)
    legacy_fonts/        # optional mapping tables               (FR-EX-05)
    normalize.py         # text_raw -> text rules                (FR-EX-07)
    layout.py            # header/footer removal, line grouping  (FR-EX-08)
    segmenter.py         # units, verse refs, page joins         (FR-EX-09..11)
    quality.py           # score + flags                         (FR-EX-12, 13)
    writer.py            # JSONL + report, deterministic         (FR-EX-14, NFR-EX-02)
  tests/
    fixtures/ (generated PDFs, gold/*.txt)
    contract/ unit/ acceptance/
```

## Data flow (per document)

```
open PDF ─► for each page:
              spans+fonts ─► classify ─┬─ ok ─────────► text-layer lines
                                       ├─ broken/image ► render 300dpi ─► OCR lines(+conf)
                                       └─ legacy ─────► map table? ─► lines  (else OCR)
          ─► layout: drop headers/footers, order lines
          ─► normalize (raw kept alongside)
          ─► segment into units, join across pages, parse verse refs
          ─► quality score + flags
          ─► write JSONL + report
```

## Key algorithms

**Page classification (FR-EX-02)**
1. No text spans and page has image covering > 50 % ⇒ `image_only`.
2. `deva_ratio` = Devanagari letters / all letters. If < 0.3 and fonts match known legacy names (list in config) ⇒ `legacy_font`.
3. `syllable_validity` = share of Devanagari clusters matching the syllable regex (consonant(+virama+consonant)* + optional matra + optional modifiers; no matra/virama at cluster start). If < 0.95 ⇒ `text_layer_broken`.
4. Otherwise `text_layer_ok`.
Thresholds live in config and are tuned on the gold set.

**Quality score (FR-EX-12)**: `score = min(deva_ratio_adj, syllable_validity, ocr_conf or 1.0)` – the weakest signal wins, simple and explainable.

**Segmentation (FR-EX-09/10)**: tokenize lines; verse terminator regex
`॥\s*(?P<num>[०-९0-9]+(?:[.\-–][०-९0-9]+)*)?\s*॥?` ; a unit closes at terminator; open unit at page end carries over to next page (FR-EX-11). Lines without any danda inside a block of > N words ⇒ `prose`.

**OCR accuracy (offline)**: Tesseract is the main accuracy risk. Levers, in order: render DPI (300 → 400), preprocessing, `--psm` page-segmentation mode per profile, `san` vs `san+hin` model order. All tuned against the gold set (AC-EX-04). If the 5 % CER target is still missed, another offline engine can be evaluated behind `OcrEngine` – a spec change, not a code-only change.

**OCR cache**: OCR results are cached on disk by page-image hash (`~/.sanskrit-extract/ocr_cache/`, keyed also by Tesseract version + settings), so re-running a book skips pages already OCR'd.

**Determinism**: sorted directory walk, no timestamps in JSONL, stable `seq`, `json.dumps(ensure_ascii=False, sort_keys=True, separators=(",", ":"))`.

## Test strategy

- **Unit**: normalizer rules (hypothesis: idempotent, NFC-preserving), syllable regex, verse-ref parser, classifier thresholds.
- **Contract**: every produced record validates against schema (AC-EX-11).
- **Acceptance**: one test per AC-EX-xx, using generated fixtures + gold set from the reference PDF `01_Chapter_Sanskrit.pdf` (Q1a, Q1b).
- **OCR quality**: CER computed with `rapidfuzz` against gold text (AC-EX-04); marked `@pytest.mark.ocr` (needs tesseract).

## Risks specific to this plan

- Tesseract `san` model accuracy on dense conjuncts may miss 5 % CER target → mitigation: preprocessing (binarize, deskew), DPI 400, page-segmentation tuning, or evaluating another offline OCR engine (spec change).
- Generating realistic broken-text-layer fixtures is tricky → keep one real sample from user PDFs if available.
