# sanskrit-extract (feature 001)

Reads Sanskrit PDFs and writes the Devanagari text, split into verses, headings and speaker lines, as JSONL
(contract: [extracted-unit 1.1.0](../specs/contracts/extracted-unit.schema.json)). It never romanizes.
Spec: [specs/001-pdf-extractor/](../specs/001-pdf-extractor/).

## Install

```sh
cd pdf-extractor
uv sync                      # library + dev tools
uv sync --extra ocr          # add OCR support (scanned PDFs)
brew install tesseract tesseract-lang   # only needed for scanned / broken pages
```

## Use

```sh
uv run sanskrit-extract ../01_Chapter_Sanskrit.pdf -o out/
uv run sanskrit-extract books/ -o out/ --pages 1-10      # also 5, 1,3-4 or 10- (to the end)
uv run sanskrit-extract book.pdf --dry-run      # page classes and OCR count, no output
```

Options: `--config file.toml`, `--profile book.toml`, `--force-ocr`, `--dpi N`, `--pages`, `--dry-run`.
Exit codes: 0 ok, 1 some files failed, 2 bad usage or Tesseract missing.

Output per PDF: `<doc_id>.jsonl` (one unit per line, reading order) and `<doc_id>.report.json`
(page classes, unit counts, flagged units, unknown legacy-font codes).

## How pages are read

| Page class | Read by |
|------------|---------|
| `text_layer_ok` | PDF text layer |
| `legacy_font` (e.g. Sanskrit99) | mapping table in `legacy_fonts/`; OCR if no table |
| `text_layer_broken`, `image_only` | Tesseract OCR (offline), cached in `~/.sanskrit-extract/ocr_cache/` |

## Config (TOML, all keys optional)

```toml
[classifier]
legacy_fonts = ["Sanskrit99"]
syllable_validity_min = 0.95

[normalize]            # each cleanup rule can be switched off
danda_spacing = true

[profile]              # or pass a separate --profile file with these keys
header_zone = 0.08
block_gap_factor = 0.75

[quality]
needs_review_below = 0.85

[ocr]
dpi = 300
languages = "san+hin"
```

## Tests

```sh
uv run pytest                 # default suite
uv run pytest -m slow -o addopts=""   # 200-page speed check
```

Tests marked `ocr` need Tesseract; tests marked `gold` need gold text in `../samples/gold/` (see its README).

## Troubleshooting: `ModuleNotFoundError: No module named 'sanskrit_extract'`

On this Mac, something sets the macOS "hidden" flag on files inside `.venv`. Python skips hidden `.pth` files,
which breaks uv's default editable install. Fix: tell uv to copy the package instead of linking it.

```sh
echo 'export UV_NO_EDITABLE=1' >> ~/.zshrc && source ~/.zshrc
```

`[tool.uv] cache-keys` in `pyproject.toml` makes `uv run` reinstall automatically after source edits.
One-off alternative: `chflags -R nohidden .venv`.
