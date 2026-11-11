# Analysis

## 1. Goal

Take PDFs containing Sanskrit slokas in Devanagari and produce, for each verse, a record that holds:

- the original Devanagari text (as extracted, and normalized),
- a romanized (Latin-script) form – this is **transliteration** (script change), not translation (meaning),
- metadata (source, page, verse number) so a RAG system can retrieve and cite it.

## 2. The hard part is extraction, not transliteration

Transliterating clean Unicode Devanagari to IAST is a solved, rule-based problem (mature libraries exist).
Getting clean Unicode Devanagari *out of a PDF* is where most projects fail. Sanskrit PDFs fall into four kinds:

| Kind | What you see when you copy text | Detection | Handling |
|------|---------------------------------|-----------|----------|
| **A. Unicode text layer** (modern, e.g. made from Word/LaTeX with Unicode fonts) | Correct Devanagari | High share of Devanagari code points (U+0900–097F), valid syllable structure | Extract text layer directly |
| **B. Unicode but broken mapping** | Devanagari letters in wrong order (e.g. `ि` before its consonant), missing virama, split conjuncts | Devanagari ratio high but syllable-validity check fails | Fall back to OCR on that page |
| **C. Legacy non-Unicode font** (Kruti Dev, Shree-Dev, Chanakya, Sanskrit 99…) | Latin junk like `vFkkr~` | Low Devanagari ratio, font names in PDF | Font-specific mapping table if available, else OCR |
| **D. Scanned images** (old printed books) | Nothing / empty | No text layer, page is an image | OCR |

So the extractor needs **per-page** classification and a fallback chain: text layer → quality check → OCR.

### OCR options

| Option | Quality on Sanskrit | Cost | Notes |
|--------|--------------------|------|-------|
| Tesseract 5 (`san` + `hin` models) | Fair to good on clean print; weaker on conjuncts and Vedic accents | Free, offline | **Chosen** (Q6: offline only). Needs `brew install tesseract tesseract-lang` (not installed on this machine yet) |
| Google Cloud Vision | Best general accuracy | 1,000 free pages/month, needs billing account | Rejected: project must run offline |
| Azure Document Intelligence (Read) | Not verified for Sanskrit | Free F0: 500 pages/month, 2 pages per request | Rejected: cloud |
| Indic-specific OCR (e.g. IndicOCR / Sanskrit-trained models) | Can be better on conjuncts | Setup heavy | Possible later plugin |

## 3. Devanagari details that affect correctness

- **Normalization**: NFC; nukta forms; stray ZWJ/ZWNJ (keep where they change rendering, record otherwise).
- **Punctuation**: danda `।` (half-verse end), double danda `॥` (verse end), verse numbers `॥ २-४७ ॥`, avagraha `ऽ`, `ॐ`.
- **Digits**: Devanagari digits `०-९` must be parsed for verse numbers, kept as-is in text.
- **Vedic accents**: udātta/anudātta (U+0951, U+0952) and the Vedic Extensions block (U+1CD0–1CFF). OCR usually loses them; transliteration schemes support them only partly.
- **Anusvara / chandrabindu / visarga**: `ं ँ ः` map to `ṃ m̐ ḥ` in IAST. No context rewriting (e.g. anusvara→homorganic nasal) in the lossless form.
- Sanskrit has **no schwa deletion** (unlike Hindi): every consonant without virama carries `a`. Libraries meant for Hindi must not be used.

## 4. Verse segmentation

Typical layout:

```
धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः ।
मामकाः पाण्डवाश्चैव किमकुर्वत सञ्जय ॥ १-१ ॥
```

Rules: a verse ends at `॥` (optionally followed/preceded by a number); `।` splits half-verses; lines are kept.
Non-verse text (headings, commentary, translations, page headers/footers, page numbers) must be classified
separately so it does not pollute verses. Verses can cross a page break.

## 5. Romanization schemes

| Scheme | Example (कृष्णः) | Lossless | Use |
|--------|------------------|----------|-----|
| IAST | kṛṣṇaḥ | Yes | Default display + embeddings |
| ISO 15919 | kr̥ṣṇaḥ | Yes | Formal, distinguishes more |
| Harvard-Kyoto | kRSNaH | Yes | ASCII, case-sensitive |
| ITRANS | kRRiShNaH | Yes | ASCII, common online |
| SLP1 | kfzRaH | Yes | One char per phoneme; good for exact-match indexing |
| ASCII-folded IAST | krsnah | **No** | What users type in a search box ("krishna"-ish) – keyword search only |

Library candidates: `indic-transliteration` (sanscript; pure Python, Sanskrit-aware, widely used) and
`aksharamukha` (more scripts, heavier). Recommendation: **indic-transliteration** as engine behind an interface;
aksharamukha as optional second engine for cross-checking.

## 6. What a RAG system needs from this

- One record per verse (a natural chunk size); commentary as separate linked records.
- Both scripts in the record: Devanagari for display/citation, IAST for embeddings, ASCII-folded for BM25 keyword match.
- Stable IDs and source citation (file, page, verse label) so answers can be traced.
- JSONL output – loads directly into most vector-store pipelines (LangChain, LlamaIndex, custom).
- Embedding/vector-store loading is **out of scope** for these two projects (a third consumer).

## 7. Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| PDFs are scanned/legacy-font → OCR errors | Wrong text in RAG | Per-page quality score + flags; review report; gold-sample tests |
| Broken text layer looks fine to code | Silent corruption | Syllable-validity check + round-trip check |
| Verse segmentation varies by book | Merged/split verses | Configurable segmentation profiles per document |
| Vedic accents appear despite "none" (Q3) | Wrong romanization | Phase 1 detects + flags them for review; full support in Phase 2 |
| Non-sloka text appears despite "slokas only" (Q2) | Noise in RAG | Classified `other` + `needs_review`; visible in report |
| "English script" misunderstood as translation | Wrong deliverable | Confirmed as transliteration; translation listed as future work |

## 8. Decisions taken (defaults; see open-questions.md)

1. Two independent Python packages in one repo, coupled only by JSON Schema contracts.
2. PyMuPDF for text layer + page rendering. OCR: Tesseract only, fully offline (Q6).
3. `indic-transliteration` for romanization; **IAST is the only output by default** (Q4, confirmed). Other schemes are opt-in.
4. JSONL output, one verse/unit per line.
