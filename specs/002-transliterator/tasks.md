# 002 – Transliterator: Tasks

Same rules as 001: tests first, one task at a time, cite requirement IDs. 002 can start in parallel with 001
because it depends only on the contract (use hand-written sample `extracted-unit` JSONL as input fixtures).

| ID | Task | Satisfies | Tests to write first | Depends |
|----|------|-----------|----------------------|---------|
| TR-T01 | Scaffold `transliterator/` package, CLI `sanskrit-romanize --version` | constitution 9, 11 | `test_cli_version` | – |
| TR-T02 | Contract harness for both schemas + hand-written input fixtures | NFR-TR-01, 05 | valid/invalid samples | T01 |
| TR-T03 | `engines/base.py` + `sanscript_engine.py`; scheme table tests | FR-TR-02, 10 | AC-TR-01 (letters), AC-TR-03 | T01 |
| TR-T04 | `postprocess.py` (dandas, digits, avagraha, ॐ, chandrabindu) + `accents.py` | FR-TR-04, 05, 06 | AC-TR-01, AC-TR-04, AC-TR-10 | T03 |
| TR-T05 | ASCII fold (optional scheme, off by default – lowest priority, may be deferred) | FR-TR-03 | AC-TR-02 | T04 |
| TR-T06 | `script_runs.py`: detect non-Devanagari units and skip them with a warning (mixed-script runs are Phase 2) | FR-TR-08 | AC-TR-07 | T03 [P] |
| TR-T07 | `roundtrip.py` | FR-TR-07 | AC-TR-05, AC-TR-06, property test | T04 |
| TR-T08 | `api.py` `romanize()` | FR-TR-13 | api table tests | T05, T06 |
| TR-T09 | `rag_view.py` | FR-TR-09 | AC-TR-09 | T08 |
| TR-T10 | `io.py` read/validate/write, report, determinism; line alignment | FR-TR-01, 11, NFR-TR-02, 04 | AC-TR-08, AC-TR-11, AC-TR-12 | T09 |
| TR-T11 | `cli.py` full options | FR-TR-12 | AC-TR-11 via CLI | T10 |
| TR-T12 | Optional `aksharamukha_engine.py` + `--cross-check` | FR-TR-10 | disagreement report test | T11 [P] |
| TR-T13 | E2E with extractor output | AC-TR-13 | AC-TR-13 | T11 + EX-T13 |
| TR-T14 | Benchmark | NFR-TR-03 | `@slow` | T11 |
| TR-T16 | Readable `.romanized.txt` output | FR-TR-14 | AC-TR-15 | T10 |
| TR-T17 | `convert.sh`: one command PDF → romanized, fails on any loss | AC-TR-13, AC-EX-19 | e2e run | T13 |
| TR-T18 | Mixed-script units: romanize Devanagari parts, keep Latin words | FR-TR-08 | AC-TR-16 | T06 |
| TR-T19 | `--pages` filter by source pages | FR-TR-15 | AC-TR-17 | T11 |
| TR-T20 | One text file per sloka, configurable name prefix | FR-TR-16 | AC-TR-18 | T19 |
| TR-T15 | Package README | – | – | T11 |

## Traceability

| Requirement | Tasks | Acceptance |
|-------------|-------|-----------|
| FR-TR-01 | T10 | AC-TR-11 |
| FR-TR-02 | T03 | AC-TR-01, 03, 08 |
| FR-TR-03 | T05 | AC-TR-02 |
| FR-TR-04 | T04 | AC-TR-04 |
| FR-TR-05 | T04 | AC-TR-01 |
| FR-TR-06 | T04 | AC-TR-10 |
| FR-TR-07 | T07 | AC-TR-05, 06 |
| FR-TR-08 | T06 | AC-TR-07 |
| FR-TR-09 | T09 | AC-TR-09 |
| FR-TR-10 | T03, T12 | table tests, cross-check test |
| FR-TR-11/12 | T10, T11 | AC-TR-11 |
| FR-TR-13 | T08 | api tests |
| NFR-TR-01/02/04 | T02, T10 | AC-TR-12 |
| NFR-TR-03 | T14 | benchmark |
| NFR-TR-05 | T02 | no import of `sanskrit_extract` (checked by test) |
