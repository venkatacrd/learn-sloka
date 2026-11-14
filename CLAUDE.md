# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Four independent Python tools for Bhagavad Gita material. Each is its own `uv` project, run by shell scripts in the
repo root.

| Project | CLI | Does |
|---------|-----|------|
| `pdf-extractor/` (001) | `sanskrit-extract` | PDF → Devanagari units as JSONL (`extracted-unit` contract) |
| `transliterator/` (002) | `sanskrit-romanize` | extracted JSONL → IAST JSONL, readable `.txt`, optional one file per sloka |
| `audio-splitter/` (003) | `sloka-split` | chapter recitation MP3 → one MP3 per sloka + offline review page |
| `recitation-coach/` (004) | `recite-serve`, `recite-check`, `recite-setup` | local practice page: record a sloka, get pronunciation feedback |

The projects never import each other:
- 001 and 002 share **only** the versioned JSON schemas in `specs/contracts/`. 002 bundles them via hatch
  `force-include`, and `contracts.py` falls back to the repo copy when run from source.
- 003 and 004 read other tools' output files.
- Small helpers (e.g. the `--pages` parser in `pages.py`) are deliberately duplicated rather than shared.

## Rules (enforced: read `specs/constitution.md`)

- **Spec first.** No behaviour without a requirement in `specs/<feature>/spec.md`. Order: spec row (FR/NFR + AC) →
  `tasks.md` row → failing test → code. This applies to the root scripts too.
- **Tests are named after acceptance IDs.** Every `AC-XX-NN` has a test whose name contains it (`test_AC_EX_28_…`), so
  `pytest -k AC_EX_28` finds it.
- **Offline at runtime.** No network or cloud services; the coach's model download (`recite-setup`) is the only
  exception.
- **Deterministic.** Same input ⇒ identical bytes.
- **Code style.** Library + thin CLI (no logic in `cli.py`); Python 3.12; `mypy --strict` on `src/`; ruff, line
  length 120.
- **Contracts.** A breaking change bumps the major version.

## Commands

Always set these first: on this Mac `.venv` files get the macOS hidden flag, which breaks editable installs (see
`pdf-extractor/README.md` › Troubleshooting).

```sh
export UV_NO_EDITABLE=1; unset VIRTUAL_ENV
```

Per project (`cd <project>`):

```sh
uv sync --all-extras          # extras: extractor `ocr` (Tesseract), transliterator `crosscheck` (aksharamukha)
uv run pytest                 # -q; extractor + transliterator also skip `slow` benchmarks
uv run pytest -k AC_EX_28     # one acceptance criterion
uv run ruff check . && uv run ruff format --check . && uv run mypy
```

From the repo root. Scripts call tools via `uv run --project <dir>` rather than `cd`, so relative paths in options
keep working.

```sh
./convert-chapters.sh [pdf] [--chapters 18] [--no-source]   # book → output/pdf/<pdf>/slokas/CHnn_sloka_NN.txt
./convert.sh [pdf] [--pages 9-16] [--sloka-prefix X_] [--sloka-no-source]   # extract + romanize
./extract-pdf.sh [pdf] [out] [--pages 9-16] [-- extractor options]
./convert-text.sh output/pdf/<pdf>/extracted [out] [--pages …] [--sloka-prefix …]   # → sibling romanized/
./split-audio.sh ["<chapter>.mp3"] [out] -- [--name CH02] [--expected 72] [--text <romanized.jsonl>]
./practice.sh [--text <pdf name>] [--audio <recording name>] [--port 8770]   # all chapters by default
./build-executables.sh [tool …]   # PyInstaller binaries → dist/ (rebuild after code changes)
```

**Folder layout** (FR-TR-17, FR-AS-13, FR-RC-13):
- **Inputs:** `input/pdf/`, `input/mp3/`, and `input/recordings/` (the author's practice takes). A bare file name is
  looked up there; no file name means every file, one run each.
- **Outputs mirror them:**
  - `output/pdf/<pdf stem>[_pages-<range>]/{extracted,romanized}/`, plus `chapters/CHnn/` and `slokas/` from
    `convert-chapters.sh`
  - `output/mp3/<recording stem>/`
- A second positional argument overrides the output folder.
- Every script **empties its output folder first** (refusing a folder that holds its input) and exits non-zero if its
  loss check fails.
- `--pages` (`5`, `1-10`, `1,3-4`, `10-`) means PDF positions: in `SrimadBhagawadGeeta_Sanskrit.pdf` chapter 1 is pages
  9–16, chapter 18 pages 122–133, and printed numbers are offset by 8.

## Architecture

**Extractor** (`pipeline.py` drives it):
- **Pipeline:** `pdf_reader` (PyMuPDF lines with font/size/bbox + horizontal separator rules) → `page_classifier` →
  read via the text layer, the **Sanskrit99 legacy-font table** (`legacy_fonts/`) or Tesseract OCR (`ocr/`, cached in
  `~/.sanskrit-extract/ocr_cache`) → `layout.remove_headers_footers` → `normalize` → `segmenter` → `quality` →
  records + report.
- **Invariant:** `coverage.lines_read = lines_in_units + lines_removed` (`unaccounted` must be 0). Every removed line is
  listed with its reason.
- **Header/footer removal:** bare page numbers; text repeated in the margin zone on ≥ 50 % of all, odd or even pages;
  lines outside document-wide separator rules; small-font margin lines repeated on ≥ 2 pages. Between the rules the
  zone checks are off, so body lines like `॥ ॐ श्री परमात्मने नमः ॥` survive.
- **Segmenter:** units are verse / heading / speaker / other, with verse numbers, colophons and `split_by_speaker`.
  - Headings are narrow lines centred on the **text frame**, measured separately for odd and even pages, because the
    reference book mirrors its margins.
  - Speaker lines end in `उवाच`, also when joined by sandhi (`भगवानुवाच`, written with the vowel sign ु).
- `--verify-ocr` cross-checks every unit with a second, OCR read.

**Transliterator** (`io.process_file`):
- **Pipeline:** validate against the input contract → optional `--pages` filter on `source.page_start/end` →
  `unit.romanize_unit` (`sanscript`, `postprocess` for dandas/digits/avagraha) → **round-trip check** (IAST and,
  when produced, Telugu → Devanagari must equal the source) → validate the output contract → JSONL + report + `.txt`.
- `telugu` is an output "scheme" (a script, FR-TR-19): stored in `romanized.telugu` / `romanized_lines.telugu`,
  Telugu digits, dandas kept. The root scripts always produce it; `.txt` and sloka files show Devanagari, Telugu, IAST.
- An optional aksharamukha cross-check engine compares every unit.
- `sloka_files.py` names files by **verse number**. Speaker lines attach to the next verse, or mid-verse for
  `split_by_speaker`. Unnumbered verses are skipped, and repeated verse numbers are an error, so files are made one
  chapter at a time (`convert-chapters.sh` does this per chapter).

**Audio splitter:**
- **Lossless cuts:** `mp3frames` parses MPEG frames so parts are whole-frame copies (Xing/Info and tags dropped). The
  joined parts must equal the source frames byte for byte.
- **Analysis:** `analysis` decodes to 16 kHz mono (miniaudio, no ffmpeg).
  - A voice segment between pauses ≈ one line (pāda).
  - Tail pitch per segment is split by Otsu into falling *cadence* or not; every half-verse has one cadence.
  - `half_verse_end` (auto/cadence/next) picks the line that ends each half-verse from the pause lengths. On the
    reference recording the pitch falls on lines 1 and 3, and lines 2 and 4 end the half-verses (**user-verified by
    ear**).
  - Pauses shorter than 0.75 × the typical in-half-verse pause are breaths inside a line.
- **A right sloka count does not prove the cuts are right.**
- **Output:** `splitter` writes ID3-tagged parts, `.splits.json`, Audacity `.labels.txt`, and `review.py`'s
  self-contained `.review.html`. `--name` sets the file stem.

**Recitation coach:**
- **Pipeline:** `model` → `normalize` → `compare` → `feedback`.
  - `model` runs the Su-śrotā Sanskrit ASR (ONNX INT8, pinned revision + SHA-256, onnxruntime only) and keeps a time
    and probability per output character.
  - `normalize` puts the expected and heard text in one comparison form, tracking which word each letter came from:
    sandhi joins, anusvāra → class nasal, and म्/ं treated alike before non-class consonants.
  - `compare` runs a weighted Levenshtein (vowel sign ↔ consonant costs more), splits differences per akṣara and
    classifies them. It applies the accepted variants (held final vowel at line end, र्य→र्ज) and sets confidence
    (`REPORT_MIN_PROB` 0.4; a dropped visarga is always unsure).
  - `feedback` turns findings into IAST sentences + JSON.
- **Library:**
  - `library` splits each printed half-verse into two pādas by syllables.
  - `load_book` splits a whole book into chapters: a new chapter starts where the verse number restarts, and its
    number comes from the `अथ <ordinal>ोऽध्यायः` heading (non-chapter parts are dropped).
  - It matches each `output/mp3/*Ch NN*` folder to its chapter and flags chapters whose audio part count differs from
    the book.
- **Server and page:**
  - `server` uses the stdlib, binds 127.0.0.1 only and checks the `Host` header. Its API is
    `/api/chapters`, `/api/sloka/C/N`, `/audio/C/N` and `POST /api/check/C/N`.
  - `static/index.html` records with MediaRecorder and sends 16 kHz WAV.
- **Tuning:** thresholds and variants were tuned on the instructor's 47 chapter-1 slokas (≤ 1 false finding per
  sloka) and the takes in `input/recordings/`. Re-measure with `tests/test_audio.py` after changing them.

## Data

- **Not in git:** PDFs, MP3s, `output/`, `dist/` and `.build/`. Only the empty `input/*/.gitkeep` folders are
  committed.
- **Tests that need real files skip when they're missing.**
  - `input/pdf/SrimadBhagawadGeeta_Sanskrit.pdf` (reference book)
  - `input/pdf/01_Chapter_Sanskrit.pdf` (chapter-1 reference; currently absent, so those tests skip)
  - `input/mp3/1_Ch 01 Complete.mp3`
  - The coach's real-audio tests also need `output/pdf/SrimadBhagawadGeeta_Sanskrit/` (`./convert-chapters.sh`) and
    `output/mp3/1_Ch 01 Complete/` (`./split-audio.sh`).
- **Stray folder:** `pdf-extractor/{{HOMEBREW_PREFIX}}/` is an empty folder created by a system library. Ignore it.
