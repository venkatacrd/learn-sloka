# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Three independent Python tools for Sanskrit (Bhagavad Gita) material, each its own `uv` project, plus root shell
scripts that run them:

| Project | CLI | Does |
|---------|-----|------|
| `pdf-extractor/` (feature 001) | `sanskrit-extract` | PDF → Devanagari units as JSONL (`extracted-unit` contract) |
| `transliterator/` (feature 002) | `sanskrit-romanize` | extracted JSONL → IAST JSONL, readable `.txt`, optional one file per sloka |
| `audio-splitter/` (feature 003) | `sloka-split` | chapter recitation MP3 → one MP3 per sloka + offline review page |
| `recitation-coach/` (feature 004) | `recite-check`, `recite-serve`, `recite-setup` | local practice page: record a sloka, get pronunciation feedback |

The projects never import each other. 001 and 002 are coupled **only** through the JSON schemas in
`specs/contracts/` (002 bundles them at build time via hatch `force-include`; `contracts.py` falls back to the repo
copy when run from source). 003 is independent. Small shared helpers (e.g. the `--pages` parser in
`pages.py`) are deliberately duplicated rather than shared.

## Spec-driven process (enforced — read `specs/constitution.md`)

- No behaviour without a requirement in `specs/<feature>/spec.md`; update spec → `tasks.md` → tests → code.
- Every acceptance criterion `AC-XX-NN` has a test whose name contains the ID (`test_AC_EX_25_...`), so
  `pytest -k AC_EX_25` finds it. Add new FR/NFR/AC rows and a task row when adding behaviour.
- Contracts are versioned; breaking changes bump the major version and both projects validate against them.
- Fully offline at runtime (no network, no cloud services); deterministic output (same input ⇒ identical bytes);
  library + thin CLI (no business logic in `cli.py`); Python 3.12, `mypy --strict` on `src/`, ruff line length 120.
- `specs/004-recitation-coach/brainstorm.md` is a parked idea (pronunciation feedback), not a spec.

## Commands

Always run uv with these set (on this Mac the `.venv` files get the macOS hidden flag, which breaks editable
installs — see `pdf-extractor/README.md` › Troubleshooting):

```sh
export UV_NO_EDITABLE=1; unset VIRTUAL_ENV
```

Per project (`cd pdf-extractor`, `transliterator` or `audio-splitter`):

```sh
uv sync --all-extras                        # extractor extra: ocr (Tesseract); transliterator extra: crosscheck (aksharamukha)
uv run pytest                               # addopts: -q; extractor + transliterator also -m "not slow" (benchmarks)
uv run pytest tests/acceptance/test_extractor_acceptance.py -k AC_EX_25    # one test
uv run ruff check . && uv run ruff format --check . && uv run mypy
```

From the repo root (run tools via `uv run --project <dir>`, not `cd`, so relative paths in options keep working):

```sh
./convert.sh [pdf] [--pages 9-16] [--sloka-prefix 1_Ch_01_sloka_] [--sloka-no-source]   # both PDF steps
./convert-chapters.sh [pdf] [--chapters 18] [--with-source]   # whole book → output/pdf/<pdf>/slokas/CHnn_sloka_NN.txt
./extract-pdf.sh [pdf] [out] [--pages 9-16] [-- extra extractor options]
./convert-text.sh output/pdf/<pdf>/extracted [out] [--pages 9-16] [--sloka-prefix ...]     # → sibling romanized/
./split-audio.sh ["<chapter>.mp3"] [out] -- --expected 47 --text output/pdf/<pdf>/romanized/<doc>.romanized.jsonl
./practice.sh [--text <pdf name>] [--audio <recording name>] [--port 8770]   # coach page, all chapters (model → ~/.recite-coach/)
./build-executables.sh [tool ...]            # PyInstaller one-file binaries → dist/ (rebuild after code changes)
```

**Folder layout** (FR-TR-17, FR-AS-13, FR-RC-13): inputs in `input/pdf/`, `input/mp3/` (and practice takes in
`input/recordings/`); a bare file name is looked up there and no input means every file in the folder, one run each.
Outputs mirror it: `output/pdf/<pdf stem>[_pages-<range>]/{extracted,romanized}/` and `output/mp3/<recording stem>/`.
An explicit output folder (2nd positional) overrides. `practice.sh` uses the only text/audio in `output/` or asks
for a name. Each script **empties its output folder first** (with guards against deleting a folder that holds its input) and
exits non-zero if its loss check fails. `--pages` syntax everywhere: `5`, `1-10`, `1,3-4`, `10-`; numbers are PDF page
positions (in `SrimadBhagawadGeeta_Sanskrit.pdf` chapter 1 is pages 9–16; printed numbers are offset by 8).

## Architecture (big picture)

**Extractor** (`pdf-extractor/src/sanskrit_extract/pipeline.py` drives it):
`pdf_reader` (PyMuPDF lines with font/size/bbox, plus horizontal separator rules) → `page_classifier` (text layer ok /
broken / legacy font / image) → read via text layer, the **Sanskrit99 legacy-font table** (`legacy_fonts/`), or
Tesseract OCR (`ocr/`, cached in `~/.sanskrit-extract/ocr_cache`) → `layout.remove_headers_footers` → `normalize` →
`segmenter` (verse / heading / speaker / other; verse numbers, colophons, `split_by_speaker`) → `quality` → records +
report. Invariant checked by tests and scripts: `coverage.lines_read = lines_in_units + lines_removed`
(`unaccounted` must be 0); every removed line is listed with a reason. Header/footer removal combines: bare page
numbers, text repeated in the margin zone on ≥50 % of all/odd/even pages, lines outside document-wide separator
rules, and small-font margin lines repeated on ≥2 pages; between the rules the zone checks are off, so body lines like
`॥ ॐ श्री परमात्मने नमः ॥` survive. `--verify-ocr` cross-checks units with a second OCR read.

**Transliterator** (`io.process_file`): validate each line against the input contract → optional `--pages` filter by
`source.page_start/end` → `unit.romanize_unit` (script runs, `sanscript` engine, `postprocess` for dandas/digits/avagraha,
accents) → **round-trip check** IAST → Devanagari must equal the source (`roundtrip_ok`) → validate output contract →
JSONL + report + `.txt`. Optional aksharamukha cross-check engine. `sloka_files.py` writes one file per sloka named by
**verse number** (speaker lines attach to the next verse, or mid-verse for `split_by_speaker`); repeated verse numbers
(several chapters) are an error — one chapter at a time.

**Audio splitter**: `mp3frames` parses MPEG frames so cuts are **lossless frame copies** (no re-encode; Xing/Info and
tags dropped; after each run the joined parts must equal the source frames byte for byte). `analysis` decodes to 16 kHz
mono (miniaudio, no ffmpeg): voice segments between pauses ≈ one line (pāda); tail pitch per segment split by Otsu
into falling *cadence* vs not; every half-verse has one cadence. Which line ends the half-verse is decided from pause
lengths (`half_verse_end` auto/cadence/next) — on the reference recording the pitch falls on lines 1 and 3 and lines
2/4 end the half-verses (**user-verified by ear**; an earlier version cut one line early while the sloka count was
still right, so counts alone don't prove cut correctness). Short pauses (< 0.75 × typical in-half-verse pause) are
breaths inside a line. `splitter` writes parts with ID3 tags, `.splits.json`, Audacity `.labels.txt`, and
`review.py`'s self-contained `.review.html` (per-file start/end playback, marks, export).

**Recitation coach** (`recitation-coach/`, feature 004): `model` runs the Su-śrotā Sanskrit ASR (ONNX INT8, pinned
revision + SHA-256, onnxruntime only) and keeps a time and probability per output character → `normalize` puts
expected and heard Devanagari in one comparison form while tracking which word/char each letter came from (sandhi
join, class-nasal/anusvāra, म्/ं before non-class consonants) → `compare` does a weighted Levenshtein (vowel sign vs
consonant costs more), splits differences per akṣara, classifies the kind, applies accepted variants (held final
vowel at line end, र्य→र्ज), sets confidence (`REPORT_MIN_PROB` 0.4, dropped visarga always unsure) → `feedback`
builds IAST sentences and JSON → `server` (stdlib, 127.0.0.1 only, Host check) serves `static/index.html`, which
records with MediaRecorder and sends 16 kHz WAV. `library` splits each printed half-verse into its two recited lines
(pādas) by syllables, and `load_book` splits a whole book into chapters (verse-number restarts + `अथ <ordinal>ोऽध्यायः`
headings) and matches `output/mp3/*Ch NN*` folders; chapters whose audio part count differs from the book are flagged. Thresholds and variants were tuned on the instructor's 47 slokas (≤ 1 false finding per sloka)
and the author's takes in `input/recordings/` — re-measure with `tests/test_audio.py` after changing them.

## Data and outputs

PDFs and audio are git-ignored (copyrighted/large); only the empty `input/*/.gitkeep` folders are committed. Put
`01_Chapter_Sanskrit.pdf`, `SrimadBhagawadGeeta_Sanskrit.pdf` in `input/pdf/` and `1_Ch 01 Complete.mp3` in `input/mp3/`.
Tests needing them skip when absent; the coach's real-audio tests also need `output/pdf/SrimadBhagawadGeeta_Sanskrit/` and
`output/mp3/1_Ch 01 Complete/` (run `convert-chapters.sh` / `split-audio.sh`). `output/`, `dist/`, `.build/` are ignored. `pdf-extractor/{{HOMEBREW_PREFIX}}/` is a stray empty
folder created by a system library — ignore it.
