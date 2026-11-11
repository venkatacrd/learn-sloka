# Open Questions

Each question has a default so work is not blocked. Resolve before the listed task starts.

## Resolved

| ID | Question | Decision | Date | Spec impact |
|----|----------|----------|------|-------------|
| Q1 | Are the PDFs digital or scanned? | **Both / not sure.** Phase 1 supports both: read the text layer where it is good, OCR the rest (current FR-EX-02..05). The real mix will be measured from the sample PDFs (see Q1a). | 2026-11-07 | none (spec already covers both) |
| Q1a | Which PDF is the Phase 1 reference input? | **`01_Chapter_Sanskrit.pdf`** (project root, 4 pages): Bhagavad Gita ch. 1, verses 1–47, Word 2013, digital (no images). Devanagari is set in **Sanskrit99**, a legacy non-Unicode font (see Q9). Cambria is used only for page numbers, so Q2 (slokas only) holds. Layout: two columns, running header, speaker lines (`… उवाच -`), one speaker line inside verse 21, colophon on p4. Gold text format: `samples/gold/README.md`. | 2026-11-07 | EX-T03, EX-T11 |
| Q1b | Gold text for the reference PDF? | **Optional (revised 2026-11-08).** No manual work after sharing a PDF. Accuracy is checked automatically instead (Q11). Gold files, if ever added to `samples/gold/`, are still used by the tests; without them those tests skip. | 2026-11-08 | EX-T03, AC-EX-04 (skips without gold) |
| Q2 | Do the PDFs mix in commentary or translation? | **Slokas only.** No commentary or translation. Besides verses, only headings / colophons (e.g. `इति … अध्यायः`) are expected. | 2026-11-07 | FR-EX-09, FR-TR-08 |
| Q3 | Vedic accent marks? | **None in Phase 1.** Accent support moves to the Phase 2 backlog. Phase 1 only detects and flags accents so a wrong assumption is noticed. | 2026-11-07 | FR-EX-13, FR-TR-06 |
| Q4 | Which romanization(s) are needed? | **IAST only.** Other schemes and the plain-ASCII form stay available as opt-in config, off by default. | 2026-11-07 | FR-TR-02, FR-TR-03, FR-TR-09 |
| Q5 | Is translation into English *meaning* also wanted? | **No.** Purpose is script conversion: Devanagari → romanized (IAST). | 2026-11-07 | Confirms 002 scope; translation stays out of scope |
| Q6 | Cloud OCR acceptable? | **No – fully offline.** Tesseract is the only OCR engine; the tools make no network calls. (Google Cloud Vision's free tier was considered and dropped.) | 2026-11-07 | FR-EX-04, FR-EX-17, FR-EX-18, NFR-EX-05 |
| Q7 | Verse numbering formats in the books? | **All of them**: `॥ १ ॥`, `॥ २-४७ ॥` / `॥२.४७॥`, and ASCII `1.47`. | 2026-11-07 | FR-EX-10 (unchanged) |
| Q8 | Which RAG stack consumes the output? | **Phase 2.** RAG is the goal of the next stage. Phase 1 writes generic JSONL with a store-neutral `rag` block (`text_for_embedding` = IAST) and no store-specific code. | 2026-11-07 | FR-TR-09 (unchanged); P2-03 |
| Q9 | The reference PDF uses the legacy **Sanskrit99** font: mapping table or OCR? | **Mapping table first.** Build a Sanskrit99 → Unicode table (exact, deterministic, fast); OCR is the fallback for unmapped glyphs and for scanned pages. Confirmed by measurement: once Q1b gold text exists, compare error rate of mapping vs. OCR on those pages. | 2026-11-07 | FR-EX-05 (unchanged); EX-T11 |
| Q10 | How are speaker lines (`… उवाच -`) handled? | **Own unit** of new type `speaker`. A verse interrupted by a speaker line (Gita 1.21) stays one `verse` with flag `split_by_speaker`, followed by the `speaker` unit. Contract `extracted-unit` bumped to 1.1.0 (additive). | 2026-11-08 | FR-EX-09, AC-EX-18, FR-TR-08, extracted-unit 1.1.0 |
| Q11 | How is accuracy checked with no manual work? | **Automatic second reading.** Every unit read from the text layer or a legacy-font table is also OCR'd (Tesseract, offline) line by line, and the two readings are compared; units that clearly disagree are flagged `ocr_disagreement` for review. Transliteration can likewise be cross-checked by a second engine. Measured on the reference PDF (2026-11-08): Tesseract misreads ~10 % of characters on correct text, so the OCR check catches gross failures only (threshold CER 0.40), not single-character table errors. The second transliteration engine (aksharamukha) agrees with the default engine on all 57 units. Gives confidence, not proof. | 2026-11-08 | FR-EX-20, AC-EX-20/21, extracted-unit 1.2.0, convert.sh |

## Open

| ID | Question | Default if unanswered | Blocks |
|----|----------|-----------------------|--------|
| – | *No open questions.* | | |

## Phase 2 backlog

Items deliberately left out of Phase 1. Each needs a spec change before any code.

| ID | Item | Origin |
|----|------|--------|
| P2-01 | Vedic accent (svara) support: preserve in extraction, OCR, and IAST output; round-trip with accents | Q3 |
| P2-02 | Commentary / translation text in PDFs (`prose` units, non-Devanagari runs). *Partly done 2026-11-08:* Latin words inside a Devanagari unit are kept as-is while the Devanagari is romanized (FR-TR-08). | Q2 |
| P2-03 | RAG integration: choose the vector store / embedding model, load the JSONL, and adjust the `rag` block if needed | Q8 |
