# 002 – Transliterator: Technical Plan

Implements [spec.md](spec.md).

## Stack

| Concern | Choice | Why |
|---------|--------|-----|
| Engine | **indic-transliteration** (`sanscript`) | Sanskrit-oriented, supports IAST/ISO/HK/ITRANS/SLP1/Velthuis, pure Python |
| Cross-check engine | `aksharamukha` (optional extra `[crosscheck]`) | Independent implementation to catch engine bugs |
| Validation | `jsonschema` | Input + output contracts |
| CLI / config / tests | `typer`, `pydantic` + TOML, `pytest` + `hypothesis` | Same as 001 for consistency |

## Layout

```
transliterator/
  pyproject.toml
  src/sanskrit_romanize/
    cli.py                # thin CLI                               (FR-TR-12)
    api.py                # romanize(text, scheme)                 (FR-TR-13)
    config.py
    engines/
      base.py             # TransliterationEngine protocol         (FR-TR-10)
      sanscript_engine.py
      aksharamukha_engine.py
    script_runs.py        # split text into Devanagari / other runs (FR-TR-08)
    postprocess.py        # dandas, digits, avagraha, ascii fold    (FR-TR-03..05)
    accents.py            # Vedic accent handling                   (FR-TR-06)
    roundtrip.py          # IAST -> Devanagari compare              (FR-TR-07)
    rag_view.py           # builds rag block                        (FR-TR-09)
    io.py                 # read/validate input, write output       (FR-TR-01, 11)
  tests/ unit/ contract/ acceptance/ e2e/
```

## Flow per unit

```
validate input ─► script runs ─► for each Devanagari run:
                                   engine(dev→scheme) ─► postprocess(scheme)
                ─► same for each line
                ─► ascii = fold(iast)        (only if enabled)
                ─► roundtrip(iast→dev) == text ?
                ─► rag view
                ─► validate output ─► write
```

## Notes

- Post-processing is applied **after** the engine so engine upgrades do not change our conventions; it is per scheme and tested with tables.
- Round-trip compares against `extracted.text` after applying the same danda/digit conventions in reverse, so convention choices do not cause false failures.
- `romanize()` in `api.py` is the same code path as batch mode – used by the RAG side to normalize user queries typed in Devanagari, IAST or ASCII.
- Engine version is recorded in every record (`engine_version`) – required for determinism and audits.

## Test strategy

- **Table tests** (AC-TR-01..04): a CSV of Devanagari → expected per scheme, curated from standard references (Gita 1.1, 2.47; tricky cases: `ज्ञ`, `क्ष`, `ऋ ॠ ऌ`, `ऽ`, `ँ`, `ॐ`, conjunct chains).
- **Property tests**: for random valid Devanagari syllable strings, IAST round-trips (hypothesis strategy built from the syllable grammar in 001's `syllables.py`, copied, not imported – NFR-TR-05).
- **Contract tests**: input and output schemas.
- **E2E** (AC-TR-13): runs 001 CLI then 002 CLI on the gold PDF in a temp dir.
