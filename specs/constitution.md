# Constitution

Non-negotiable rules for both projects. A spec, plan, task or code change that breaks one of
these must be rejected or must amend this file first (with a reason).

## Process

1. **Spec before code.** No code is written for a behavior that is not in a `spec.md`.
   If implementation reveals a gap, update the spec first, then the code.
2. **Traceability.** Every task in `tasks.md` cites the requirement IDs (`FR-`, `NFR-`) it satisfies.
   Every requirement has at least one acceptance criterion (`AC-`), and every AC has an automated test
   whose name contains the AC ID (e.g. `test_AC_EX_03_unicode_text_layer`).
3. **Test first.** For each task: write the failing acceptance/unit test, then the code, then refactor.
4. **Contracts are versioned.** The JSON schemas in `specs/contracts/` are the only coupling between
   the two projects. Breaking changes bump the major version; both projects validate against them in tests.

## Data fidelity

5. **Never silently change the source text.** The extractor keeps `text_raw` exactly as extracted.
   Any cleanup is a separate field (`text`) produced by documented, deterministic rules.
6. **No guessing.** If text cannot be read reliably (bad font encoding, low OCR confidence), the record is
   flagged, not "fixed" by heuristics that invent characters.
7. **Lossless transliteration.** The primary romanization must round-trip back to the identical
   normalized Devanagari. Lossy forms (plain ASCII) are labeled as such and are never the only output.
8. **Unicode NFC everywhere.** All text fields are NFC-normalized UTF-8.

## Engineering

9. Python 3.12, `pyproject.toml`, `uv` for environments, `pytest`, `ruff`, type hints with `mypy --strict` on library code.
10. Deterministic output: same input file + same config + same version ⇒ byte-identical JSONL.
11. Each project is a library with a thin CLI on top; the CLI holds no business logic.
12. **Fully offline.** No network calls at runtime and no cloud services or SDKs. Source PDFs never leave the machine.
