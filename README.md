# Sanskrit Script Conversion

Local, offline tools for Bhagavad Gita study material:

- **PDF reader**: reads Sanskrit PDFs (Devanagari slokas) into clean text, dropping page headers and footers.
- **Text converter**: turns that text into romanized IAST, with one file per sloka if you want.
- **MP3 splitter**: cuts a chapter recitation into one MP3 per sloka.
- **Recitation coach**: a practice page in your browser that plays the instructor, records you, and points out
  pronunciation mistakes.

Each tool is a separate Python project, started by a script in this folder.

## Quick start

Needs [uv](https://docs.astral.sh/uv/) (it installs Python 3.12 and each tool's packages on first run). Optional:
`brew install tesseract tesseract-lang` for the OCR cross-check.

```sh
export UV_NO_EDITABLE=1          # once per terminal (see pdf-extractor/README.md › Troubleshooting)

# 1. put the book in input/pdf/ and the chapter recordings in input/mp3/
./convert-chapters.sh            # book → output/pdf/<book>/slokas/CH01_sloka_01.txt … CH18_sloka_78.txt
./split-audio.sh "1_Ch 01 Complete.mp3" -- --name CH01 --expected 47    # one chapter → output/mp3/1_Ch 01 Complete/
./practice.sh                    # practice page at http://127.0.0.1:8770/  (Ctrl+C to stop)
```

## Folders

```
input/                     you put files here (not in git; only the empty folders are)
  pdf/                       Sanskrit PDFs
  mp3/                       chapter recitations
  recordings/                your own practice takes (used by the recitation-coach tests)
output/                    the scripts write here (not in git)
  pdf/<pdf name>/            one folder per PDF (<pdf name>_pages-80-93/ when --pages is used)
    extracted/                 Devanagari text units + report
    romanized/                 IAST text + readable .txt + report
    chapters/CH01 … CH18/      per-chapter text and sloka files (convert-chapters.sh)
    slokas/                    all sloka files together (convert-chapters.sh)
  mp3/<recording name>/      one MP3 per sloka + review page
```

Give a script a bare file name and it looks in `input/pdf/` or `input/mp3/`; give no file and it processes every
file there. Any path works too, and a second argument sets a different output folder. **Every script empties its
output folder before it runs** (and refuses to empty a folder that holds its input).

## Commands

| Command | What it does |
|---------|--------------|
| `./convert-chapters.sh [pdf] [--with-source]` | Whole book → one IAST file per sloka, named by chapter and sloka (`CH02_sloka_47.txt`). Finds each chapter's pages by itself. `--with-source` adds the Devanagari. |
| `./convert.sh [pdf] [--pages 9-16]` | PDF → `extracted/` + `romanized/` in one go. |
| `./extract-pdf.sh [pdf] [--pages 9-16]` | PDF reader only → `extracted/`. |
| `./convert-text.sh <…/extracted> [--pages 9-16]` | Text converter only → the `romanized/` folder next to it. |
| `./split-audio.sh [mp3] -- [--name CH01] [--expected 47]` | Recording → one MP3 per sloka. `--name` sets the file names, `--expected` checks the count. |
| `./practice.sh [--audio "<recording>"]` | Recitation coach page: whole book, all chapters. |
| `./build-executables.sh` | Standalone programs in `dist/` (see below). |

**Common options**

- `--pages 5`, `1-10`, `1,3-4` or `10-` (to the end). These are positions in the PDF file, not printed page
  numbers (in `SrimadBhagawadGeeta_Sanskrit.pdf` chapter 1 is pages 9–16).
- `--sloka-prefix NAME_` (`convert.sh`, `convert-text.sh`): also write `slokas/NAME_01.txt`, `NAME_02.txt`, …, one
  per sloka, named by verse number, with its speaker line (`sañjaya uvāca -`) included. `--sloka-no-source` makes
  them IAST only. Use one chapter at a time, since verse numbers restart per chapter; `convert-chapters.sh` does
  this for the whole book.
- Options for the underlying tool go after `--`, e.g. `./extract-pdf.sh book.pdf -- --force-ocr`.

## How each tool checks its work

Every script prints a summary and exits non-zero if anything was lost or failed.

| Tool | What happens | Check |
|------|--------------|-------|
| PDF reader ([pdf-extractor/](pdf-extractor/)) | Reads each page from its text layer, a legacy-font table (Sanskrit99) or offline OCR; removes page numbers and running headers/footers; splits the rest into verses, headings and speaker lines. | Every line read is either in the output or listed in the report with the reason it was removed. Unknown font codes are reported, never guessed. If Tesseract is installed, every unit is also read by OCR and big differences are flagged. |
| Text converter ([transliterator/](transliterator/)) | Converts each line to IAST. | Each line converted back to Devanagari must equal the original exactly. A second engine (aksharamukha) converts it too and any difference is flagged. |
| MP3 splitter ([audio-splitter/](audio-splitter/)) | Finds lines from pauses and half-verses from falling pitch; copies whole MP3 frames (no re-encoding). | The parts joined back equal the original byte for byte. `--expected N` flags a wrong sloka count. `<name>.review.html` lets you check every cut by ear. |
| Recitation coach ([recitation-coach/](recitation-coach/)) | A local speech model writes down what you said; it is compared with the sloka letter by letter. | Tuned so the instructor's own recitation gets at most 1 false finding per sloka on average. |

The coach downloads its speech model (~180 MB, Su-śrotā by Prof. Prathosh A P, IISc) once into `~/.recite-coach/`;
after that nothing goes online. Personal and family use only; see
[recitation-coach/README.md](recitation-coach/README.md).

Converter output (`output/pdf/<pdf name>/`):

- `romanized/<doc>.romanized.txt`: readable, Devanagari lines then IAST lines, unit by unit
- `romanized/<doc>.romanized.jsonl`: one record per unit (Devanagari, IAST, verse number, page, citation, search fields)
- `extracted/<doc>.report.json`, `romanized/<doc>.romanized.report.json`: what was read, removed and flagged

## Standalone executables

`./build-executables.sh` (~5 min) builds `dist/sanskrit-extract`, `dist/sanskrit-romanize` and `dist/sloka-split`.
They need no Python or uv and take the same options as the tools, but:

- they run only on the kind of machine they were built on;
- they must be rebuilt after code changes;
- they don't empty the output folder first, except `sloka-split --clean`.

```sh
dist/sanskrit-extract input/pdf/book.pdf -o output/pdf/book/extracted --verify-ocr
dist/sanskrit-romanize output/pdf/book/extracted -o output/pdf/book/romanized --strict --cross-check
dist/sloka-split "input/mp3/1_Ch 01 Complete.mp3" -o "output/mp3/1_Ch 01 Complete" --clean --expected 47
```

## Development

Code is written from the specs, in this order: [constitution](specs/constitution.md) →
[analysis](specs/00-analysis.md) → per feature `spec.md` (requirements and acceptance criteria) → `plan.md` →
`tasks.md` → a test named after each acceptance ID → code. Open decisions are in
[specs/open-questions.md](specs/open-questions.md).

| Feature | Spec |
|---------|------|
| 001 PDF reader | [specs/001-pdf-extractor/](specs/001-pdf-extractor/) |
| 002 Text converter | [specs/002-transliterator/](specs/002-transliterator/) |
| 003 MP3 splitter | [specs/003-audio-splitter/](specs/003-audio-splitter/) |
| 004 Recitation coach | [specs/004-recitation-coach/](specs/004-recitation-coach/spec.md): increment 1 (practice page) built; increment 2 (family profiles, history) next |

Per project: `cd <project> && uv run pytest`, and `uv run ruff check . && uv run mypy` for lint and types.
See [CLAUDE.md](CLAUDE.md) for commands and architecture notes.

**Test data.** PDFs, MP3s, outputs and executables are not in git. Tests that need them are skipped when they're
missing; to run them, put `SrimadBhagawadGeeta_Sanskrit.pdf` (and `01_Chapter_Sanskrit.pdf`) in `input/pdf/`,
`1_Ch 01 Complete.mp3` in `input/mp3/`, then run `./convert-chapters.sh` and `./split-audio.sh "1_Ch 01 Complete.mp3"`.
`samples/gold/` holds hand-checked text for a few pages that extraction accuracy is tested against.
