# sloka-split (feature 003)

Splits a chanted recitation MP3 into one MP3 per sloka. Spec: [specs/003-audio-splitter/](../specs/003-audio-splitter/).

```sh
./split-audio.sh "1_Ch 01 Complete.mp3"                    # from the repo root; empties audio-outs/ first
./split-audio.sh "1_Ch 01 Complete.mp3" -- --expected 47   # also check the sloka count

cd audio-splitter && UV_NO_EDITABLE=1 uv run sloka-split <mp3-or-folder> -o <outdir> [--clean] [--expected N]
```

How it finds slokas: each line (pāda) is a stretch of voice between pauses. Every half-verse has exactly one line
that ends on a falling pitch (a cadence, ~125 Hz vs ~165 Hz on the reference file). Which line actually ends the
half-verse is decided from the pauses (the pause after a half-verse is longer): on the reference recording the pitch
falls on lines 1 and 3, so lines 2 and 4 end the half-verses. Override with `--half-verse-end cadence|next`.
A sloka is 2 half-verses (`--half-verses-per-sloka`). Very short pauses (a breath inside a line) never end a sloka.
Monotone material before the first / after the last sloka becomes `_intro.mp3` / `_closing.mp3`; a speaker line
(`sañjaya uvāca`) stays with the sloka it introduces.

Cuts are lossless: whole MP3 frames are copied, nothing is re-encoded, and after every run the tool checks that
the parts joined back give the original audio byte for byte. No ffmpeg needed.

Review the cuts: open `<name>.review.html` (written next to the MP3s) in a browser. For each file, ▶ Start / ▶ End
play just the first / last 5 s; mark it OK or wrong (keys `1`–`5`, `j`/`k` to move), then *Export findings* to get
`<name>.review-findings.json`. Marks stay in the browser between visits. Add each sloka's text with
`--text ../text-outs/<doc>.romanized.jsonl` (output of `convert-text.sh`). Alternatively open the original MP3 in
Audacity, *File › Import › Labels…* and pick `<name>.labels.txt`.

Exit codes: 0 ok · 1 doubtful split (`count_mismatch`, `no_cadence_pattern`, `incomplete_last_sloka`,
`half_verse_end_uncertain`, `coverage_failed`; files are still written) · 2 usage/IO error.

Limits: needs a reciter whose half-verse cadence is clearly lower; 6-pāda verses shift the pairing (use
`--expected` to catch it).

Tests: `uv run pytest` (synthetic chants + an end-to-end run on `../1_Ch 01 Complete.mp3` when present).
