# Sanskrit Script Conversion

Turns Sanskrit PDFs (Devanagari slokas) into clean, romanized, RAG-ready records.

```
 PDFs ──► [001 pdf-extractor] ──► extracted/*.jsonl ──► [002 transliterator] ──► romanized/*.jsonl ──► RAG ingestion
          (Devanagari, as-is)     (contract: extracted-unit)                    (contract: romanized-unit)
```

The PDF reader and text converter are separate projects that only share the JSON contracts in
[specs/contracts/](specs/contracts/); either can be rewritten without touching the other. The MP3 splitter
(feature 003) is independent of both.

## Folders: put files in `input/`, results appear in `output/`

```
input/                         you put files here (git-ignored, only the empty folders are committed)
  pdf/                           Sanskrit PDFs, e.g. SrimadBhagawadGeeta_Sanskrit.pdf
  mp3/                           chapter recitations, e.g. "1_Ch 01 Complete.mp3"
  recordings/                    your own practice takes (used by the recitation-coach tests)
output/                        the scripts write here, same split (git-ignored)
  pdf/<pdf name>/                  one folder per PDF (…/<pdf name>_pages-80-93/ when --pages is used)
    extracted/                     Devanagari units (PDF reader)
    romanized/                     IAST + readable .txt (text converter); slokas/ with --sloka-prefix
  mp3/<recording name>/            one MP3 per sloka + review page (MP3 splitter)
```

A bare file name is looked up in `input/pdf/` or `input/mp3/`, and with no file name a script processes every file in
its input folder. You can still pass any path, and an explicit output folder as the 2nd argument.

## The tools

Each is a separate program (own project, own dependencies) with its own command at the repo root.
Every command empties its output folder before it runs and refuses to empty a folder that holds its input.

| Command | Tool | Input → output |
|---------|------|----------------|
| `./convert.sh [pdf] [--pages 9-24]` | PDF reader + text converter in one go | `input/pdf/` → `output/pdf/<pdf>/{extracted,romanized}/` |
| `./convert-chapters.sh [pdf] [--with-source]` | Whole book → one IAST file per sloka, by chapter | `input/pdf/` → `output/pdf/<pdf>/slokas/CH01_sloka_01.txt …` (and `chapters/CHnn/`) |
| `./extract-pdf.sh [pdf] [--pages 9-24]` | PDF reader ([pdf-extractor/](pdf-extractor/)) | `input/pdf/` → `output/pdf/<pdf>/extracted/` |
| `./convert-text.sh <…/extracted> [--pages 9-24]` | Text converter ([transliterator/](transliterator/)) | `…/extracted/` → the `romanized/` folder next to it |
| `./split-audio.sh [mp3]` | MP3 splitter ([audio-splitter/](audio-splitter/)) | `input/mp3/` → `output/mp3/<recording>/` |
| `./practice.sh` | Recitation coach ([recitation-coach/](recitation-coach/)) | reads `output/pdf/` + `output/mp3/`; local page: play the instructor, record yourself, get pronunciation feedback |

**One file per sloka:** add `--sloka-prefix <name>` to `convert-text.sh` or `convert.sh` to also write
`slokas/<name>01.txt`, `<name>02.txt`, … (number = verse number, padded like the audio files; Devanagari lines, a blank
line, then IAST; a speaker line such as `सञ्जय उवाच -` is included with its sloka). `--sloka-files` does the same with
the prefix `sloka_`. Add `--sloka-no-source` for IAST-only sloka files (no Devanagari). Use one chapter at a time (pick it with `--pages`): verse numbers restart per chapter.

```sh
./convert.sh 01_Chapter_Sanskrit.pdf --sloka-prefix 1_Ch_01_sloka_
#   → output/pdf/01_Chapter_Sanskrit/romanized/slokas/1_Ch_01_sloka_01.txt …
./convert.sh SrimadBhagawadGeeta_Sanskrit.pdf --pages 17-30 --sloka-prefix 2_Ch_02_sloka_
#   → output/pdf/SrimadBhagawadGeeta_Sanskrit_pages-17-30/…
```

`--pages` takes `5`, `1-10`, `1,3-4` or `10-` (to the last page); numbers are positions in the PDF file, not the
printed page numbers. On the PDF reader it reads only those pages (pages the PDF does not have are reported); on the
text converter it converts only units from those PDF pages.
Other options for the underlying tool go after `--`, e.g. `./extract-pdf.sh book.pdf -- --force-ocr`.

Running headers and footers are left out of the extracted text (and so of the conversion): page numbers, lines
repeated in the page margins (also book-style headers that alternate between odd and even pages), anything outside
the page's header/footer separator rules, and small-font margin lines that repeat. Each removed line is listed in
`<doc>.report.json` → `removed_lines`.
Each exits non-zero if its loss check fails.

```sh
export UV_NO_EDITABLE=1                 # once, see pdf-extractor/README.md › Troubleshooting
./convert.sh                            # every PDF in input/pdf/
./convert.sh SrimadBhagawadGeeta_Sanskrit.pdf --pages 9-16       # chapter 1 of the full book
./extract-pdf.sh 01_Chapter_Sanskrit.pdf                          # or the two steps separately
./convert-text.sh output/pdf/01_Chapter_Sanskrit/extracted
```

### Standalone executables (no Python or uv needed)

```sh
./build-executables.sh          # ~5 min → dist/sanskrit-extract, dist/sanskrit-romanize, dist/sloka-split
dist/sanskrit-extract input/pdf/01_Chapter_Sanskrit.pdf -o output/pdf/01_Chapter_Sanskrit/extracted --verify-ocr
dist/sanskrit-romanize output/pdf/01_Chapter_Sanskrit/extracted -o output/pdf/01_Chapter_Sanskrit/romanized --strict --cross-check
dist/sloka-split "input/mp3/1_Ch 01 Complete.mp3" -o "output/mp3/1_Ch 01 Complete" --clean --expected 47
```

Single-file binaries (PDF reader ~175 MB because of OpenCV, text converter ~30 MB, MP3 splitter ~20 MB) with the same
options as the `uv run` commands and byte-identical output. They run on the OS/CPU they were built on (rebuild on each
platform), and must be rebuilt after code changes. OCR still needs Tesseract installed. The `*.sh` scripts above
run from source via `uv`, not the binaries. Unlike the scripts, the binaries do not empty the output folder first
(except `sloka-split --clean`).

| Step | What happens | Loss check |
|------|--------------|------------|
| 1. Extract ([pdf-extractor/](pdf-extractor/)) | Every page is read: text layer, legacy-font table (Sanskrit99) or offline OCR. Lines are cleaned, headers/page numbers removed, and the rest split into `verse` / `heading` / `speaker` / `other` units. | Every line read is either in a unit or listed in the report with its reason (`coverage.unaccounted` must be 0); unknown font codes are reported, never guessed. |
| 2. Romanize ([transliterator/](transliterator/)) | Each unit and each of its lines → IAST. | Every unit is converted back IAST → Devanagari and must equal the source exactly (`roundtrip_ok`). |
| Check | Each script prints a summary of its tool's report. | Exit code ≠ 0 if anything was lost or failed. |

Automatic accuracy checks, no manual work (Q11):

- **OCR cross-check**: every unit is also read by Tesseract and compared (needs `brew install tesseract tesseract-lang`;
  skipped with a note otherwise). Units more than 40 % different are flagged for review. Tesseract misreads ~10 % of
  characters even on correct text, so this catches gross failures (wrong font table, garbled page), not single letters.
- **Second transliteration engine**: every unit is also romanized by aksharamukha; any difference is flagged.

First run OCRs every line (~10 s per page); results are cached in `~/.sanskrit-extract/ocr_cache/`.

Results in `output/pdf/<pdf name>/`:

- `romanized/<doc>.romanized.txt` – readable: Devanagari lines, then IAST lines, unit by unit
- `romanized/<doc>.romanized.jsonl` – one record per unit (Devanagari, IAST, verse number, page, citation, RAG fields)
- `extracted/<doc>.report.json` and `romanized/<doc>.romanized.report.json` – what was read, removed, flagged

## Split a chapter recording into slokas (feature 003)

```sh
./split-audio.sh "1_Ch 01 Complete.mp3" -- --expected 47 \
    --text output/pdf/01_Chapter_Sanskrit/romanized/01-chapter-sanskrit-438e578c.romanized.jsonl
```

Open `output/mp3/<name>/<name>.review.html` to check every cut by ear (sloka text shown when `--text` is given). Writes `<name>_intro.mp3`, `<name>_sloka_01.mp3 … _sloka_47.mp3`, `<name>_closing.mp3`,
plus `<name>.splits.json` (cut times, checks) and `<name>.labels.txt` (Audacity labels for reviewing the cuts).
Lossless (MP3 frames are copied, not re-encoded); independent of features 001/002. See
[audio-splitter/README.md](audio-splitter/README.md).

## Practise reciting (feature 004)

```sh
./practice.sh                                   # whole book: chapter picker, audio from output/mp3/
./practice.sh --audio "1_Ch 02 Complete"        # only one chapter's instructor audio
```

Opens http://127.0.0.1:8770/; Ctrl+C stops it. See [recitation-coach/README.md](recitation-coach/README.md).

## How this project is built: spec-driven development

Code is written **from the specs**, not from ad-hoc prompts. Order of work:

| Step | Artifact | Purpose |
|------|----------|---------|
| 0 | [specs/constitution.md](specs/constitution.md) | Rules every spec, plan and line of code must follow |
| 1 | [specs/00-analysis.md](specs/00-analysis.md) | Problem analysis, risks, technology choices |
| 2 | `spec.md` per feature | *What* and *why*: requirements (FR-/NFR-) and acceptance criteria (AC-) |
| 3 | `plan.md` per feature | *How*: architecture, modules, libraries, data flow |
| 4 | `tasks.md` per feature | Ordered, small tasks; each cites the requirement IDs it satisfies |
| 5 | Implementation | One task at a time: write the acceptance test first, then the code |

Features:

- [specs/001-pdf-extractor/](specs/001-pdf-extractor/) – read PDFs, extract Devanagari text faithfully, segment into verses
- [specs/002-transliterator/](specs/002-transliterator/) – convert Devanagari to romanized IAST (other schemes opt-in), verify losslessness
- [specs/003-audio-splitter/](specs/003-audio-splitter/) – split a chanted chapter MP3 into one MP3 per sloka
- [specs/004-recitation-coach/](specs/004-recitation-coach/spec.md) – record yourself reciting a sloka and get pronunciation feedback (offline, one Mac); increment 1 (practice page) built, increment 2 (family profiles, history) next; background in [brainstorm.md](specs/004-recitation-coach/brainstorm.md)

## Sample data

PDFs and MP3s are **not in git** (`.gitignore`), nor are generated outputs or built executables. To use the examples
in this README and run the tests that need real input, put `01_Chapter_Sanskrit.pdf` and
`SrimadBhagawadGeeta_Sanskrit.pdf` in `input/pdf/`, `1_Ch 01 Complete.mp3` in `input/mp3/`, and (for the coach's
real-audio tests) run `./convert-chapters.sh` and `./split-audio.sh "1_Ch 01 Complete.mp3"`. Without
them those tests are skipped and everything else still passes.

```
samples/
  pdfs/   # Phase 1 source PDFs (digital, scanned, or both)
  gold/   # correct text for a few pages: <pdf-name>_p<page>.txt, one sloka line per line
```

The gold files are the reference that extraction and OCR accuracy are tested against.

Open decisions are tracked in [specs/open-questions.md](specs/open-questions.md) and must be resolved
(or explicitly defaulted) before the matching task starts.
