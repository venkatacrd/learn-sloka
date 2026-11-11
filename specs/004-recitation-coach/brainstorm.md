# 004 – Recitation Coach: Brainstorm

Status: **Idea – parked (2026-11-10).** No spec, plan or code yet. Next step when resumed: the de-risking
experiment below.

## Goal

The learner records themselves reciting one sloka; the app finds pronunciation mistakes and replies with specific
feedback (which word, which sound, what was expected).

Available per sloka: the reference recording (feature 003, `audio-outs/<name>_sloka_NN.mp3`) and the text
(feature 002, `--sloka-prefix` → `slokas/<name>_sloka_NN.txt`, Devanagari + IAST).

## Mistakes to catch

| Mistake | Example | Signal |
|---------|---------|--------|
| Skipped / extra / repeated word | drops *samavetā* | alignment to text or reference audio |
| Vowel length | *a/ā*, *i/ī*, *u/ū* | duration vs reference (phoneme models are weak here) |
| Sibilants | *ś / ṣ / s* | phoneme recognition |
| Retroflex vs dental | *ṭ/t*, *ṇ/n*, *ḍ/d* | phoneme recognition (harder) |
| Aspiration | *k/kh*, *d/dh* | phoneme recognition (harder) |
| Visarga / anusvāra | *yuyutsavaḥ*, *saṃ* | short-segment check at known positions |
| Rhythm / pauses | laghu/guru, pauses at line ends | timing vs reference (4-line structure known) |

## Approaches

- **A – compare with the reference recording:** time-align learner vs teacher on speaker-independent features;
  flag regions that differ; compare syllable durations and pauses. Robust, offline, no Sanskrit model needed — but it
  says *where*, not *what* ("ś became s" is out of reach).
- **B – recognize phonemes and compare with the text:** IAST → expected phonemes (near 1:1 table); a multilingual
  phoneme recognizer (e.g. wav2vec2 IPA-phoneme models) on the recording; align the two sequences → substitutions /
  omissions / insertions mapped to words. Gives the feedback we want; accuracy on Sanskrit unknown. Do **not** use
  word-level ASR (Whisper etc.): its language model "corrects" mistakes away.
- **C – hybrid:** align both recordings to the text per syllable; combine sound (B) with duration (A) to cut false
  alarms.

## Decisions so far

- **Core = B** (the user's preference; it matches the goal), **plus vowel-duration checks** from the alignment, which
  covers B's weak spot. A is a fallback signal for skipped words and timing.
- **Melody / chanting-tune feedback: future enhancement**, not in the first version.
- **Recording input: not via Claude Code's microphone.** Its voice input yields text, not audio; speech-to-text hides
  mispronunciations; Claude cannot judge audio; and it would tie the app to a dev tool and break the offline rule
  (constitution 12). Record in the app instead: a local browser page (preferred, like the review page) or a CLI
  command. Claude Code can still be used to *read and explain* the checker's results.
- Building the app with Claude Code is unaffected by any of this.

## Feedback the learner sees

Overall score; the text with words coloured green/amber/red; notes such as "*samavetā* — final ā too short",
"*kurukṣetre* — ṣ sounded like s", "skipped *pāṇḍavāś*"; for each flagged word, play teacher vs learner for just that
word. Only confident findings are shown (a false alarm costs more trust than a missed mistake).

## Risks / things to design for

- Different voice, pitch, speed and microphone → speaker normalization.
- Accepted regional variants (*ṛ* as ri/ru, *v*/*w*, *ṃ* before consonants) → configurable "accepted variants".
- Evaluation set: a few slokas recorded correctly and with deliberate mistakes (short ā, s for ś, skipped word).
- Offline: models run locally (downloaded once at setup); feedback wording from templates, not an online LLM.

## De-risking experiment (first step when resumed)

Run a phoneme recognizer on 3–5 of the *teacher's* slokas and compare with the expected phonemes from the IAST. The
teacher is correct, so the mismatch rate = model noise. Low → build B as planned; high → start with A, add B later
(possibly adapting the model on the teacher's sloka audio + text pairs). Measurement only, no project code changes.

## Plan if B holds

1. Experiment above.
2. Recording page + B (phoneme comparison) + vowel durations + skipped/extra words.
3. Accepted-variants list, progress history.
4. Future: melody feedback; more chapters (needs recordings).

## Open questions

1. Only the author, or other learners too (many voices)?
2. Strictly offline, or is an online service acceptable (e.g. nicer feedback wording)?
3. Practice on the Mac only, or also on a phone?
4. Which pronunciation tradition / regional variants count as correct?
