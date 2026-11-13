# 004 – Recitation Coach: Technical Plan

Implements [spec.md](spec.md), increment 1 (practice page).

## Stack

| Concern | Choice | Why |
|---------|--------|-----|
| Recognition | Su-śrotā ONNX INT8 via **onnxruntime** | Decided in the experiments; no PyTorch/NeMo (NFR-RC-05) |
| Audio decode (teacher MP3, CLI input) | **miniaudio** | Same as feature 003; no ffmpeg |
| IAST for words/letters in feedback | **indic-transliteration** (`sanscript`) | Same engine as feature 002, used directly (no dependency on that project) |
| Web server | Python stdlib `http.server` (`ThreadingHTTPServer`), `127.0.0.1` only | No framework needed for 4 endpoints; nothing to download at runtime |
| Page | One static HTML + JS file in the package, no external URLs | NFR-RC-01 |
| Browser recording | `MediaRecorder` → `AudioContext.decodeAudioData` → `OfflineAudioContext` at 16 kHz mono → WAV in JS | Browser-native; server receives plain WAV (FR-RC-03); `127.0.0.1` is a secure context, so the mic works |
| Model files | Downloaded once by `recite-setup` from Hugging Face, pinned revision `d320b7aada7f844b2c78d4f6c935aba77d0327a0`, SHA-256 checked, stored in `~/.recite-coach/models/` | FR-RC-13, offline afterwards |

Pinned files (SHA-256): `preprocessor.onnx` aab44917…f859 (152,338 B), `sushrota_sanskrit_ctc_int8.onnx`
6a52c782…3e64 (187,484,189 B), `sanskrit_vocab.json` be61d707…2719 (2,996 B) — full hashes in `model.py`.

## Layout

```
recitation-coach/
  src/recite_coach/
    library.py     # chapter: verses from .romanized.jsonl + teacher MP3 per sloka           (FR-RC-01)
    model.py       # model files, download/verify, transcribe -> tokens with time + prob      (FR-RC-04, 13)
    normalize.py   # Devanagari comparison form with a char->word map; rule table              (FR-RC-05)
    compare.py     # alignment, edit regions -> findings, kinds, confidence, score             (FR-RC-06–08)
    feedback.py    # IAST + plain-English sentences, JSON shape                                (FR-RC-10)
    server.py      # HTTP: page, /api/slokas, /api/sloka/N, /audio/N, POST /api/check/N        (FR-RC-03)
    static/index.html
    cli.py         # recite-check, recite-setup, recite-serve (thin)                           (FR-RC-12, 13)
  tests/
practice.sh        # repo root: setup if needed, start server (text from output/pdf/, audio from output/mp3/), open the page
```

## Flow of one check

```
WAV (page) / WAV|MP3 (CLI) -> 16 kHz mono float -> preprocessor.onnx -> ctc.onnx -> greedy tokens
  (token, frame*40 ms, softmax prob) -> heard string + per-char time/prob
expected sloka lines -> normalize (per word, sandhi join, nasal rule, speaker optional) -> expected string + per-char word
align (Levenshtein, code points) -> group consecutive differences into regions -> classify kind ->
  confidence (heard token probs; visarga always unsure) -> map to word (Devanagari, IAST), learner time span ->
  findings + score; teacher word times = same pipeline on the teacher MP3 (cached per sloka)
```

Akṣara awareness: regions are widened to whole letters (consonant + virama/matra/nasal sign) before classifying, so
`पाण्डव`→`पाण्दव` is one finding "ड→द", not two code-point edits.
