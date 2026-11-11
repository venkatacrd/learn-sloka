# 003 – Audio Splitter: Specification

Status: Draft · Independent of 001/002 (no shared contract; audio in, audio out).

## Purpose

Split a chanted recitation MP3 (e.g. one Bhagavad Gita chapter) into one MP3 per sloka, so each sloka can be
played, looped or linked on its own. Optional intro and closing parts (invocation, colophon) become their own files.

## What the audio looks like (measured on the reference file, `1_Ch 01 Complete.mp3`)

| Observation | Value |
|-------------|-------|
| Length / format | 828.8 s, MPEG-1 Layer III, 44.1 kHz stereo, VBR 192/224 kbps, no Xing header |
| Speech segments separated by pauses ≥ 0.3 s | 209 (≈ one pāda each, ~3.5 s) |
| Pauses | 0.35–1.0 s; pauses at sloka ends are **not** reliably longer than pauses inside a sloka |
| Pitch at the end of each segment | two clear groups: ~165 Hz and ~125 Hz (falling pitch = **cadence**); exactly one cadence per half-verse |
| Which line ends a half-verse | the line **after** the cadence: pitch falls at the end of lines 1 and 3, and the pause after lines 2 and 4 is longer (0.57 s vs 0.48 s; longer in 86 % of decisive cases). *Corrected 2026-11-09 after listening: the first version cut at the end of line 3.* |
| Breath inside a line | 3 pauses of 0.31–0.32 s split a line in two; normal pauses are ≥ 0.36 s |
| Cadences | 94 = 47 slokas × 2 half-verses (Gita ch. 1 has 47 slokas) |
| Before the first / after the last cadence | monotone intro (3 segments) and colophon (9 segments), no cadence |
| Speaker lines (`sañjaya uvāca`) | an extra segment without cadence before the sloka they introduce |

So sloka boundaries are found from the **melody** (every 2nd cadence marks a sloka), with pause lengths deciding
which line ends the half-verse; plain segment counting would drift whenever a speaker line or a breath splits a pāda.

## User stories

- **US-1** As a listener, I run one command on a chapter MP3 and get `…_sloka_01.mp3 … _sloka_NN.mp3`.
- **US-2** As a learner, each file starts and ends in a pause, never in the middle of a word.
- **US-3** As a maintainer, I can check the cut points by opening the original in Audacity with a labels file.
- **US-4** As an operator, a re-run gives a clean output folder (no files left from an earlier run).
- **US-5** As a reviewer, I check every cut by ear quickly — hearing just the start and end of each file next to
  the sloka's text — and record which ones are wrong.

## Functional requirements

| ID | Requirement |
|----|-------------|
| FR-AS-01 | Input: one `.mp3` file or a folder of them (non-recursive, sorted by name). |
| FR-AS-02 | Detect speech segments: 10 ms RMS energy; silence threshold = median level of non-silent frames − `silence_drop_db` (default 20 dB); pauses shorter than `min_gap_s` (0.3 s) do not split a segment; segments shorter than `min_segment_s` (0.3 s, clicks/breaths) are ignored. |
| FR-AS-03 | For each segment, estimate the pitch of its last `tail_s` (0.4 s) by autocorrelation (70–400 Hz). Split segments into *cadence* / *continuation* with a two-group threshold (Otsu) on these pitches. If the two groups are less than `min_cadence_separation_st` (2 semitones) apart, report `no_cadence_pattern` and fail. |
| FR-AS-04 | Group: each half-verse has one cadence line. `half_verse_end` says which line ends the half-verse: `cadence` (that line) or `next` (the line after it). `auto` (default) decides per file: for each cadence compare the pause after it with the pause after the next line (differences < 0.03 s do not count); the half-verse end has the longer pause. If fewer than 60 % agree → warning `half_verse_end_uncertain`. A sloka ends at the half-verse end of every `half_verses_per_sloka`-th cadence (default 2). Sloka 1 starts at the first line of the first half-verse; everything earlier is the **intro**. Every later sloka starts right after the previous one (so a speaker line belongs to the sloka it introduces). Everything after the last sloka is the **closing**. A pause shorter than 0.75 × the median pause inside a half-verse is a breath within one line and never ends a sloka. An odd number of cadences gives a last sloka with one half-verse and warning `incomplete_last_sloka`. |
| FR-AS-05 | Cut points lie at the middle of the pause after the sloka's last cadence (intro cut: middle of the pause before sloka 1), rounded to the nearest MP3 frame. |
| FR-AS-06 | Cutting is **lossless**: output files are copies of whole MP3 frames of the source (no decoding/re-encoding). ID3/APE tags and a Xing/Info/VBRI header frame of the source are not copied. |
| FR-AS-07 | Each output gets a fresh ID3v2.3 tag: title (`Sloka 1`, `Intro`, `Closing`), track (`n/N`, slokas only), album = source file name. |
| FR-AS-08 | Output names: `<stem>_intro.mp3`, `<stem>_sloka_NN.mp3` (zero-padded to the sloka count's width, min 2), `<stem>_closing.mp3`; `<stem>` = source file stem with spaces → `_`. Intro/closing are written only if non-empty. |
| FR-AS-09 | Write `<stem>.splits.json` (source, settings, chosen `half_verse_end` and its vote, every part with kind, number, start/end/duration seconds, frame range, segment and cadence counts, warnings) and `<stem>.labels.txt` (Audacity label track: `start\tend\tname`). |
| FR-AS-10 | `--expected N`: if the number of slokas found differs from N, add warning `count_mismatch` and exit 1 (files are still written for inspection). |
| FR-AS-11 | `--clean`: delete everything inside the output folder before the run. Refused (exit 2) if the output folder is the filesystem root, the home folder, or contains/equals the folder of an input file. |
| FR-AS-12 | CLI: `sloka-split <input> -o <outdir> [--clean] [--expected N] [--half-verses-per-sloka 2] [--half-verse-end auto\|cadence\|next] [--silence-drop-db 20] [--min-gap 0.3]`. Exit 0 ok, 1 warnings that mean the split is doubtful (`count_mismatch`, `no_cadence_pattern`, `incomplete_last_sloka`, `half_verse_end_uncertain`, `coverage_failed`), 2 usage/IO error. |
| FR-AS-14 | Write `<stem>.review.html`: a self-contained offline page (no network) listing every part with its time range, an audio player, buttons that play only the first / last 5 s, and status buttons (OK, ends too early, ends too late, starts wrong, other) plus a note. Shows progress, filters (all / unchecked / problems), optional auto-play of the next part, keyboard shortcuts, keeps the review in the browser's local storage, and exports the findings as `<stem>.review-findings.json` (`file`, `number`, `status`, `note` per part). |
| FR-AS-15 | `--text <file.romanized.jsonl>` (output of feature 002): the review page shows each sloka's Devanagari and IAST lines (verse *n* ↔ sloka *n*), with a preceding speaker line shown above its sloka. Without `--text` the page works without text. Unreadable text file → warning `text_unreadable`, not fatal. |
| FR-AS-13 | Root script `split-audio.sh <mp3-or-folder> [outdir=audio-outs]` always cleans the output folder, then splits. |

## Non-functional requirements

| ID | Requirement |
|----|-------------|
| NFR-AS-01 | Lossless coverage: the concatenated audio frames of all outputs are byte-identical to the source's audio frames (checked after every run; failure = exit 1). |
| NFR-AS-02 | Deterministic: same input + settings + version ⇒ byte-identical outputs and reports. |
| NFR-AS-03 | Fully offline; no ffmpeg or other system binaries (decoding via the bundled `miniaudio` wheel). |
| NFR-AS-04 | A 15-minute chapter splits in < 10 s on a laptop. |

## Acceptance criteria

| ID | Given / When / Then | Covers |
|----|---------------------|--------|
| AC-AS-01 | Synthetic chant (2 intro segments, 5 slokas of 4 pādas with high/low/high/low endings, 1 speaker segment before sloka 3, 2 closing segments) → 5 slokas, intro and closing found; sloka 3 contains the speaker segment. | FR-AS-02..04 |
| AC-AS-02 | Same, with one pāda split by a 0.35 s pause → still 5 slokas, same boundaries. | FR-AS-02, 04 |
| AC-AS-03 | Monotone audio (all segments end at the same pitch) → `no_cadence_pattern`, exit 1, no sloka files. | FR-AS-03, 12 |
| AC-AS-04 | Every cut point lies inside a pause (signal below the silence threshold ±1 frame). | FR-AS-05 |
| AC-AS-05 | Synthetic MP3 (LAME, with Info header) → outputs decode; concatenated audio frames equal the source frames; no output starts with an Info/Xing frame. | FR-AS-06, NFR-AS-01 |
| AC-AS-06 | Output tags: title `Sloka 2`, track `2/5`, album = source name; file names as FR-AS-08. | FR-AS-07, 08 |
| AC-AS-07 | `splits.json` and `labels.txt` list every part; labels parse as 3 tab-separated columns. Two runs give identical bytes. | FR-AS-09, NFR-AS-02 |
| AC-AS-08 | `--expected 6` on the 5-sloka sample → warning `count_mismatch`, exit 1, files written. | FR-AS-10 |
| AC-AS-09 | `--clean` removes a stale file from the output folder; `--clean` with the input's own folder as output → exit 2, nothing deleted. | FR-AS-11 |
| AC-AS-10 | *(e2e, skipped if the file is absent)* `1_Ch 01 Complete.mp3 --expected 47` → 47 slokas + intro + closing, `half_verse_end = next`, exit 0, < 10 s. | all, NFR-AS-04 |
| AC-AS-11 | Synthetic chant with falling pitch on lines 1 and 3 and longer pauses after lines 2 and 4 (plus a breath-split line 4) → `auto` picks `next`; every sloka contains all 4 lines. Same chant with the reference style → `auto` picks `cadence`. | FR-AS-04 |
| AC-AS-12 | `--half-verse-end` overrides `auto` and changes the cuts. | FR-AS-04, 12 |
| AC-AS-14 | Review page exists, references every written MP3, embeds no external URLs; with `--text`, sloka 2 shows its speaker line and verse 2's lines; without it, no text block. | FR-AS-14, 15 |
| AC-AS-13 | Equal pauses after every line → warning `half_verse_end_uncertain`. | FR-AS-04 |

## Known limits (Phase 2 candidates)

- Assumes the reciter's half-verse cadence is clearly lower than the pāda continuation. Other chant styles may need
  a different cue; FR-AS-03 fails loudly instead of guessing.
- Verses with 3 half-verses (6 pādas, e.g. some in chapters 1–18 other than ch. 1) shift the pairing; `--expected`
  detects this. Aligning to the extracted text (feature 001 output) could fix it.
- The first frame of each part may borrow from the previous frame's bit reservoir; since cuts are in pauses this is
  inaudible.
