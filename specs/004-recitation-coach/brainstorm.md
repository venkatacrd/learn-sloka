# 004 – Recitation Coach: Brainstorm

Status: **Experiments done; spec drafted** → [spec.md](spec.md) (2026-11-11). Originally parked 2026-11-10.

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

## Experiment A results (2026-11-10)

Setup: no learner recordings yet, so a learner was **simulated** from the teacher's sloka audio (pitch +3 semitones,
band-pass "microphone", 30 dB noise, each line 0.82–1.22× tempo, pauses 0.6–1.6×). Planted per take: one ~0.7 s cut
(skipped word) and one steady 0.36 s voiced stretch squeezed to half (short vowel). Control takes: same treatment, no
mistakes. Detector: MFCC (speaker-normalised) + DTW; flags where aligned fingerprints differ unusually, or where the
alignment squeezes speech below 60 % of the reference tempo. 2 control + 2 mistake takes per sloka.

| | v1 (global tempo), slokas 3 5 10 17 30 | v2 (local tempo, pause edges ignored), same | v2, unseen slokas 8 14 22 26 33 40 44 |
|---|---|---|---|
| Alignment error on kept speech | median 48 ms, p90 146 ms | same | median 47 ms, p90 159 ms |
| False flags per correct sloka | 3.1 | 2.1 | 2.6 |
| Skipped word caught | 9/10 | 8/10 | 11/14 |
| Short vowel caught | 2/10 | 1/10 | 4/14 |

Findings:
- **Alignment works** (≈50 ms, well within a syllable) despite different pitch, tempo, microphone and noise.
- **Skipped words: mostly caught** (~80–90 %).
- **Vowel length: not reliable with A** (10–30 %). Whole-signal alignment absorbs a shortened steady vowel; measuring
  vowel length needs to know where each vowel is, i.e. alignment to the *text* (phonemes/syllables) — part of B.
- **False alarms too high** (2–3 per sloka, target ≤ 1), mostly timing flags from natural tempo changes. Real learners
  differ in pronunciation too, not only voice, so real numbers will likely be worse.
- Optimistic by design: the "learner" is the teacher's own pronunciation, so this is a best case.

Conclusion: A alone is **not good enough for learner feedback**; it is useful as a skipped/extra-word detector and as
the time alignment that the rest builds on. This supports the chosen plan: **B (phonemes vs text) as the core, with
vowel durations taken from the text alignment**, A only for skips. Next: the B experiment (phoneme model on the
teacher's audio; needs the one-time model download), then real learner recordings (3 slokas, correct + deliberate
mistakes) to measure true false-alarm rates.

### Real recordings (2026-11-11)

Three learner takes of sloka 1 in `audio-input-test/` (git-ignored): `chapter1-sloka1-test.mp3`, `take 1 - fail.mp3`,
`take 3 - error.mp3`. Ground truth from the author: line 1 correct, mistakes in lines 2, 3 and 4 (exact mistakes not
yet listed). Automatic sloka identification picked sloka 1 for all three (clear margin only for the first).

| Take | Line 1 (correct) | Line 2 | Line 3 | Line 4 |
|---|---|---|---|---|
| chapter1-sloka1-test | 2 false flags | missed | flagged | missed |
| take 1 - fail | quiet | missed | flagged | flagged (+ extra sound) |
| take 3 - error | 5 false flags | missed | missed | missed |

Line-level: 3 of 9 mistaken lines flagged; the correct line falsely flagged in 2 of 3 takes. Worse than the
simulation — **A alone is ruled out for feedback**; its line-level time alignment did work on all three takes.

Found on the way: the splitter puts sloka 1's spoken `dhṛtarāṣṭra uvāca` into the *intro* audio, while the sloka-1 text
file starts with it — the two should agree (small fix in 002 or 003, not done yet).

Test-recording naming for future takes: `ch<CC>_sloka_<NN>_take<T>_<correct|mistakes>.mp3`, plus a same-named `.txt`
listing each deliberate mistake as `type: word — what was said` (types: skip, extra, repeat, short-vowel, long-vowel,
wrong-sound, aspiration, retroflex, sibilant, visarga, anusvara, restart).

## Experiment B results — Su-śrotā (2026-11-11)

Model: `gnumanth/sushrota-sanskrit-asr-onnx` (INT8 ONNX of `prathoshap/sushrota-sanskrit-asr` v13b, IndicConformer
fine-tuned on ~17 h of recited/chanted Sanskrit). 179 MB, `onnxruntime` + numpy only, offline, greedy CTC, no language
model; outputs Devanagari letters / letter groups (श ष स, ा, ः … distinct). Licence: personal use OK; see
"Licence" below before sharing. Comparison on Devanagari code points, spaces and punctuation removed.

**Teacher's 47 slokas (correct recitation):** character error rate **3.5 %** (121 / 3,412); 12 slokas perfect,
22 at ≤ 2 %. Much of the remainder is not model error but text-vs-speech form: sandhi across words written with a
virama + separate vowel (*pāṇḍuputrāṇām ācārya* spoken as one), speaker lines printed mid-verse (1.21, 1.28), visarga
changes before the next word. Genuine model weak spots seen: visarga often dropped (×6), य after र heard as ज in
*ācārya* (possibly the teacher's own pronunciation), occasional dropped half-letters.

**Learner takes of sloka 1 (line 1 correct, mistakes in lines 2–4):**

| Take | Line 1 | Line 2 | Line 3 | Line 4 |
|---|---|---|---|---|
| chapter1-sloka1-test | exact | समवे**द**ा (त→द) | पाण्डव (ā→a) | सञ्जय**ा** (extra ā) |
| take 1 - fail | exact | समवेत (ā→a), यु**र**युत्सव, ः dropped | पाण्**द**व (ड→द) | स**ज**या (ञ् dropped), extra ā |
| take 3 - error | exact (also heard the speaker line) | समव**द**ा, यु dropped, ः dropped | पाण्डव**ः**श्चैव (ā→ः) | किमकुर्व**क** (त→क), extra ā |

Line-level: **9 of 9 mistaken lines show differences; 0 false flags on the correct line** (option A: 3/9 and 2/3).
The model reports what was said, not the memorised text — the main risk did not show up.

Still open: whether each reported difference is the learner's actual mistake (needs the author's list); expected
single-letter noise is ~0.4 per 15-letter line on correct speech, so isolated one-letter differences need a
confidence threshold; visarga feedback is unreliable; text-vs-speech normalisation rules (sandhi, avagraha, speaker
lines) are needed before comparing.

### Licence (summary)

Su-śrotā fine-tune states no licence of its own ("observe the base model's licence"); AI4Bharat IndicConformer bases are
MIT (one generic repo CC-BY-4.0), gated; the ONNX copy is tagged Apache-2.0 without a licence file. No non-commercial
restriction found. Personal offline use: fine. Before sharing or commercial use: ask the author (Prof. Prathosh A P,
IISc) for an explicit licence and the exact base. Citation requested: "Prathosh A P, Su-śrotā: Scholar-grade Sanskrit
ASR and metre-aware chant practice, IISc Bengaluru, 2026."

**Confirmed by the author (2026-11-11):** the differences reported for the three takes are "nearly right" — they match
the mistakes actually made. Decision: **Su-śrotā (ONNX) is the model for option B**; option A is kept only for line
alignment / skipped-word timing if needed. Next: write `spec.md` for feature 004.
