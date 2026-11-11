# 002 – Transliterator: Specification

Status: Draft · Input contract: [extracted-unit 1.2.0](../contracts/extracted-unit.schema.json) ·
Output contract: [romanized-unit 1.0.0](../contracts/romanized-unit.schema.json)

## Purpose

Read the extractor's JSONL and add romanized (Latin-script) forms of each Devanagari unit, verify they are
lossless, and emit RAG-ready records. This is a script conversion (transliteration), not a translation.

## User stories

- **US-1** As an operator, I run the tool on the extractor's output folder and get romanized JSONL.
- **US-2** As a RAG engineer, each record already has text for embeddings, keyword search, display and citation.
- **US-3** As a scholar, the IAST is exact and converts back to the same Devanagari.
- **US-4** As a user searching "dharmakshetre" or "dharmaksetre", the keyword field can match.

## Functional requirements

| ID | Requirement |
|----|-------------|
| FR-TR-01 | Read one `.jsonl` file or a folder of them; validate each input line against `extracted-unit`. Invalid lines are reported and skipped, not fatal. |
| FR-TR-02 | Transliterate `extracted.text` and each of `extracted.lines` from Devanagari to **IAST**. IAST is the only output by default (Q4). Optional, off by default: `iso15919`, `hk`, `itrans`, `slp1`, `velthuis`, enabled via `--schemes`/config. |
| FR-TR-03 | *Optional, off by default.* When enabled, produce `ascii`: IAST → Unicode NFD → strip combining marks → lowercase → map `ṛ→r`, `ṣ/ś→s`, `ṅ/ñ/ṇ→n`, `ṃ→m`, `ḥ→h`; dandas → removed; collapse spaces. Labeled lossy. |
| FR-TR-04 | Handle Sanskrit specifics: inherent `a` on every consonant without virama (no schwa deletion); avagraha `ऽ→'`; `ॐ→oṃ`; anusvara `ṃ`, chandrabindu `m̐`, visarga `ḥ`; Devanagari digits → ASCII digits (configurable). Vowel hiatus is marked so IAST stays unambiguous: an independent `इ`/`उ` right after a short `a` is written `ï`/`ü` (`कइ`→`kaï`, never `kai`, which is `कै`). |
| FR-TR-05 | Dandas: `।`→`\|`, `॥`→`\|\|` by default; configurable (keep Devanagari dandas, or `.`/`..`). Verse-number labels transliterated the same way. |
| FR-TR-06 | Vedic accents (Phase 1: none expected, Q3): if a unit contains them, pass the marks through unchanged and add warning `vedic_accents_unsupported`. Proper accent romanization is Phase 2 (P2-01). |
| FR-TR-07 | **Round-trip check**: convert IAST back to Devanagari and compare (NFC) with `extracted.text`. Set `roundtrip_ok`; mismatches add a warning with the first differing position. |
| FR-TR-08 | All `verse`, `heading` and `speaker` units are Devanagari (Q2: slokas only) and are transliterated. A `mixed` unit (Devanagari plus Latin words, e.g. a contents line ending in the Roman page number `i`) has its Devanagari parts romanized and its Latin words kept exactly as they are, with warning `latin_text_kept`; the round-trip check applies to each Devanagari part. A unit with no Devanagari (`latin`) is passed through with `skipped=true`, `romanized.iast` = original text, and a warning. Full commentary/translation handling stays Phase 2 (P2-02). |
| FR-TR-09 | Build the `rag` block: `id` = unit_id; `text_for_embedding` = IAST (configurable to Devanagari); `text_for_keyword` = iast + devanagari (+ ascii first, when enabled); `display_text` = Devanagari + newline + IAST; `citation` = `"<file> p.<pages>, verse <ref>"`; `metadata` = doc_id, unit_type, verse_ref, pages, quality score, flags. |
| FR-TR-10 | Transliteration engine behind a `TransliterationEngine` interface; default `indic-transliteration`; optional `aksharamukha` for cross-check mode (`--cross-check` reports disagreements). |
| FR-TR-11 | Write `<out>/<doc_id>.romanized.jsonl` and `<out>/<doc_id>.romanized.report.json` (counts, round-trip failures, skipped units). |
| FR-TR-12 | CLI: `sanskrit-romanize <input> -o <outdir> [--pages 1-10] [--sloka-files] [--sloka-prefix P] [--schemes iast] [--config f.toml] [--cross-check]`. `--schemes` defaults to `iast`. `--strict` also exits 1 when any unit fails the round-trip check, except units the extractor flagged `invalid_syllables`: their source text is not valid Devanagari (e.g. a typo in the PDF), so no IAST can round-trip it; they are reported separately as `source_invalid`, not counted as loss. Exit codes as in extractor. |
| FR-TR-14 | Also write `<out>/<doc_id>.romanized.txt`: a readable file with, for each unit in order, its Devanagari lines followed by its IAST lines, units separated by a blank line, headed by the source file name. |
| FR-TR-15 | `--pages` (same syntax as the extractor: `5`, `1-10`, `1,3-4`, `10-`): only units whose source pages overlap the selection are converted and written. The report lists `pages_selected` and `units_outside_pages` (not counted in `units_in`, so the loss check still compares like with like). |
| FR-TR-16 | `--sloka-files` / `--sloka-prefix <prefix>`: also write one text file per sloka to `<out>/slokas/<prefix><NN>.txt` (default prefix `sloka_`). `NN` = the sloka's verse number (last number of `verse_ref.normalized`, e.g. `47` from `1.47`), zero-padded to the width of the largest number (min 2). Content: Devanagari lines, a blank line, IAST lines; with `--sloka-no-source` only the IAST lines (no Devanagari source text). A `speaker` unit goes at the top of the next verse; if that verse has flag `split_by_speaker` and the speaker follows it, the speaker line goes between the verse's first line and the rest. Headings, colophons and verses without a number are not written and are listed in the report (`sloka_files.skipped`). Repeated verse numbers (e.g. several chapters selected) → no sloka files, error `duplicate_sloka_numbers` with the numbers, exit 1. Respects `--pages`. |
| FR-TR-13 | Library API: `romanize(text: str, scheme: str) -> str` usable without files (for RAG query-time normalization of user questions). |

## Non-functional requirements

| ID | Requirement |
|----|-------------|
| NFR-TR-01 | Every output line validates against `romanized-unit.schema.json`. |
| NFR-TR-02 | Deterministic output (same as extractor rule). |
| NFR-TR-03 | ≥ 5,000 units/s for IAST-only on a laptop. |
| NFR-TR-04 | Input `extracted` object is carried over unchanged (byte-identical when re-serialized). |
| NFR-TR-05 | No dependency on the extractor package – only on the contract files. |

## Acceptance criteria

| ID | Given / When / Then | Covers |
|----|---------------------|--------|
| AC-TR-01 | `धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः ।` → IAST `dharmakṣetre kurukṣetre samavetā yuyutsavaḥ \|` | FR-TR-02, 05 |
| AC-TR-02 | *(optional scheme)* With `ascii` enabled, same input → `dharmaksetre kuruksetre samaveta yuyutsavah` | FR-TR-03 |
| AC-TR-03 | `कृष्णः` → iast `kṛṣṇaḥ`; with default config, `romanized` contains **only** the `iast` key. *(optional schemes, when enabled:)* iso15919 `kr̥ṣṇaḥ`, hk `kRSNaH`, slp1 `kfzRaH` | FR-TR-02 |
| AC-TR-04 | `सोऽहम्` → `so'ham`; `ॐ` → `oṃ`; `संस्कृतम्` → `saṃskṛtam`; `ँ` → `m̐` | FR-TR-04 |
| AC-TR-05 | For every verse in the gold set, `roundtrip_ok = true`. | FR-TR-07 |
| AC-TR-06 | A unit with a deliberately corrupted IAST engine output gets `roundtrip_ok=false` and a warning with position. | FR-TR-07 |
| AC-TR-07 | A colophon heading `इति प्रथमोऽध्यायः` → `iti prathamo'dhyāyaḥ`; a (unexpected) Latin-script unit is output with `skipped=true`, text unchanged, and a warning. | FR-TR-08 |
| AC-TR-08 | `romanized_lines[scheme]` has the same length as `extracted.lines` for every scheme. | FR-TR-02 |
| AC-TR-09 | `rag.citation` for unit on page 34, verse 2.47 of `gita.pdf` is `gita.pdf p.34, verse 2.47`. | FR-TR-09 |
| AC-TR-10 | A unit with U+0951 keeps the mark unchanged in the output and gets warning `vedic_accents_unsupported`. | FR-TR-06 |
| AC-TR-11 | Invalid input line → reported, rest of file processed, exit code 1. | FR-TR-01, 12 |
| AC-TR-12 | Running twice gives identical bytes; all outputs validate. | NFR-TR-01, 02 |
| AC-TR-14 | `कइ` → `kaï`, `प्रउग` → `praüga`, and both round-trip; `हँस` → `ham̐sa`. | FR-TR-04, 07 |
| AC-TR-15 | For each input file a `.romanized.txt` exists and contains every unit's Devanagari and IAST lines in order. | FR-TR-14 |
| AC-TR-16 | `गीताध्यानश्लोकाः ..... i` (script `mixed`) → `gītādhyānaślokāḥ ..... i`, `skipped=false`, `roundtrip_ok=true`, warning `latin_text_kept`. | FR-TR-08 |
| AC-TR-17 | Input with units on pages 1, 2 and 3; `--pages 2` → only the page-2 units are written, `units_outside_pages` = the others, `units_in = units_out`; a unit spanning pages 1–2 is included; `--pages 0` → exit 2. | FR-TR-15 |
| AC-TR-18 | Chapter 1 JSONL with `--sloka-prefix 1_Ch_01_Complete_sloka_` → `slokas/1_Ch_01_Complete_sloka_01.txt … _47.txt`; `_02.txt` starts with `सञ्जय उवाच -` and `sañjaya uvāca -`; in `_21.txt` `अर्जुन उवाच -` is the 2nd Devanagari line; headings/colophon are only in `sloka_files.skipped`. With `--pages` covering verses 6–9 only `_06…_09` are written. Two units with verse number 1 → error `duplicate_sloka_numbers`, exit 1, no sloka files. | FR-TR-16 |
| AC-TR-19 | `--sloka-files --sloka-no-source` → each sloka file holds only the IAST lines (speaker line included), no Devanagari character and no blank separator line; the `.romanized.txt` and JSONL are unchanged. | FR-TR-16 |
| AC-TR-13 | End-to-end: extractor output for the gold PDF → transliterator → every verse has IAST + round-trip OK. | Integration of 001+002 |

## Out of scope

Phase 2 backlog (Vedic accents, mixed-script/commentary text – see open-questions.md); translation to English meaning (possible feature 003); sandhi splitting / word segmentation; embedding or loading into a vector store; other Indic source scripts.
