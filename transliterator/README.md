# sanskrit-romanize (feature 002)

Reads the extractor's JSONL and adds IAST (other schemes opt-in), checking every unit converts back to the
identical Devanagari. Spec: [specs/002-transliterator/](../specs/002-transliterator/).

```sh
cd transliterator
export UV_NO_EDITABLE=1
uv run sanskrit-romanize ../output/extracted -o ../output/romanized --strict
uv run sanskrit-romanize in.jsonl --schemes iast,hk,ascii      # extra schemes
uv run sanskrit-romanize ../output/extracted --pages 9-16     # only units from PDF pages 9-16
uv run sanskrit-romanize ../output/extracted --sloka-prefix ch01_sloka_   # + slokas/ch01_sloka_01.txt …
```

Options: `--schemes`, `--config f.toml` (`danda_style = "pipe"|"devanagari"|"period"`, `digits = "ascii"|"devanagari"`,
`embedding_text = "iast"|"devanagari"`), `--cross-check` (needs `uv sync --extra crosscheck`), `--strict`.

Library: `from sanskrit_romanize.api import romanize; romanize("कृष्णः")  # 'kṛṣṇaḥ'`

Conventions: `।`→`|`, `॥`→`||`, `ऽ`→`'`, `ँ`→`m̐`, Devanagari digits → ASCII, vowel hiatus `कइ`→`kaï`.
Vedic accent marks are kept unchanged with a warning (Phase 2).

Tests: `uv run pytest` (the end-to-end test also runs ../pdf-extractor).
