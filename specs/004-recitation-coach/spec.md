# 004 – Recitation Coach: Specification

Status: Draft (2026-11-11) · Background, experiments and decisions: [brainstorm.md](brainstorm.md)
Inputs: per-sloka teacher audio (feature 003) and per-sloka text (feature 002 `.romanized.jsonl`).

## Purpose

A learner recites one sloka into the microphone and gets specific pronunciation feedback: which word, which sound,
what was expected and what was heard. Phase 1 is **offline, on one Mac, for the author and family**; more users,
devices and feature areas come later, once the basics are accepted (see Phase 2).

## Increments

1. **Practice page (first build):** FR-RC-01, 03–08, 10, 12, 13 — show the sloka, play the instructor, record, submit,
   get feedback; CLI and setup. ACs 01, 03–06, 08–12.
2. **Family use:** FR-RC-02 profiles, FR-RC-11 history, FR-RC-09 accepted variants (file seeded in increment 1, page
   action in 2). ACs 02, 07.

## Decisions behind this spec

| Topic | Decision (brainstorm reference) |
|---|---|
| How mistakes are found | Speech recognition of the learner's recitation compared with the sloka text (option B) |
| Model | Su-śrotā Sanskrit ASR, ONNX INT8 copy (`gnumanth/sushrota-sanskrit-asr-onnx`, ~179 MB). On 3 real takes it reported the actual mistakes (author: "nearly right") with no false flags on the correct line; teacher CER 3.5 % |
| Not used | Waveform comparison with the teacher (option A, ruled out); Claude Code's microphone; online services |
| Melody / chanting tune | Phase 2 |
| Users | Author and family, one shared Mac, simple learner profiles (no passwords) |
| Licence | Personal/family use is fine; ask the model author before any sharing (brainstorm › Licence) |

## User stories

- **US-1** As a learner, I pick my name and a sloka, see its Devanagari and IAST, listen to the teacher, record myself
  and get feedback within seconds.
- **US-2** As a learner, the feedback names the word and the sound ("*samavetā*: heard *samaveta* — the final ā is long")
  instead of a vague score.
- **US-3** As a learner, I can play the teacher's version and mine of just the flagged word.
- **US-4** As a learner, I see my attempts per sloka over time and which kinds of mistakes I repeat.
- **US-5** As a family member, I have my own profile and history on the same Mac.
- **US-6** As the maintainer, I can check a recording from the command line (and from Claude Code) without the page.

## Functional requirements

| ID | Requirement |
|----|-------------|
| FR-RC-01 | **Sloka library.** Built from a configured chapter: teacher audio folder (`audio-outs/`, files `<name>_sloka_NN.mp3`) and the converter's `<doc>.romanized.jsonl` (Devanagari + IAST lines per verse, speaker line attached to the next verse, or inside a `split_by_speaker` verse). A sloka without audio or text is listed as unavailable, not hidden. |
| FR-RC-02 | **Learner profiles.** Create/select/rename a learner by display name; each has its own history folder. No passwords. Deleting a learner deletes their recordings and history after confirmation. |
| FR-RC-03 | **Practice page.** A local web page (served on `127.0.0.1` only) shows learner, sloka picker, the sloka text (Devanagari + IAST), teacher playback, and Record / Stop / Submit. Recording uses the browser microphone and is sent as 16 kHz mono 16-bit WAV (encoded in the page, no codec dependency). The page loads no external URLs. |
| FR-RC-04 | **Recognition.** The recording is transcribed with the Su-śrotā ONNX model (preprocessor + CTC, greedy decoding). For every output token keep its time (40 ms frames) and its probability. |
| FR-RC-05 | **Text normalisation** before comparing, applied to both the expected text and the transcript: remove spaces, dandas, digits, hyphens and `ऽ`; join words across sandhi written with a virama + independent vowel (e.g. `णाम् आचार्य` ≡ `णामाचार्य`); treat anusvāra and the homorganic nasal + virama as equal (`ं` ≡ `ङ्`/`ञ्`/`ण्`/`न्`/`म्` before a consonant of that class), and `म्` ≡ `ं` before य र ल व श ष स ह; collapse a vowel sign the model repeats (`मिि` → `मि`); the speaker line (`… उवाच`) is optional — compare with and without it and keep the better match. Rules live in one table so variants can be added (FR-RC-09). |
| FR-RC-06 | **Comparison.** Align expected vs heard Devanagari (edit distance on akṣara-aware units) and map every difference to its line and word. Each difference becomes a finding with: line, word (Devanagari + IAST), expected letters, heard letters, kind, confidence, learner time span. |
| FR-RC-07 | **Kinds of finding:** vowel length (ā/a, ī/i, ū/u), retroflex ↔ dental (ट/त, ड/द, ण/न), sibilant (श/ष/स), aspiration (क/ख, ग/घ, …), voicing (क/ग, त/द, ट/ड, प/ब, च/ज), nasal (ञ ङ ण न म ं), missing letter, extra letter, substituted letter, visarga, missing word, extra/repeated word. |
| FR-RC-08 | **Confidence.** A finding is *reported* only if the heard tokens involved have probability ≥ `report_min_prob` (default **0.4**, tuned on the instructor's 47 slokas: 0.74 reported findings per correct sloka) or one side spans ≥ 2 letters; otherwise it is *unsure* and shown only when "show unsure" is on. A *dropped* visarga is always *unsure* (model weak spot); a visarga heard in place of another letter is a normal finding. |
| FR-RC-09 | **Accepted variants.** A per-chapter TOML list of equivalences that are not mistakes (e.g. `य` after `र` heard as `ज`), seeded with the rules from FR-RC-05 plus: `र्य` heard as `र्ज` (the reference reciter's own pronunciation of *ācārya*), and a final vowel held long at the end of a line (chanting convention: *janārdana* → *-nā*, *sañjaya* → *-yā*); a finding can be marked "this is acceptable" on the page, which adds it to the list after confirmation. |
| FR-RC-10 | **Feedback view.** Overall score (% of expected letters said correctly), the sloka with each word coloured (correct / reported finding / unsure), and per finding a plain sentence in English with IAST, e.g. "*pāṇḍava*: heard **d** (dental) instead of **ḍ** (retroflex)". Buttons play the teacher's and the learner's audio for that word only; the teacher's word times come from transcribing the teacher audio once (cached). |
| FR-RC-11 | **History.** Each submission is stored per learner: WAV, transcript, findings, score, timestamp, model version. The page shows attempts per sloka (score trend) and the learner's most frequent finding kinds. The learner can delete any attempt. |
| FR-RC-12 | **CLI** `recite-check <recording> --sloka N [--chapter cfg] [--json]`: same pipeline, prints the findings (or JSON). Accepts WAV and MP3. Exit 0 = no reported findings, 1 = findings, 2 = usage/IO error. |
| FR-RC-13 | **Setup.** `recite-setup` (and a root script `practice.sh`) downloads the model files once into a local model folder and verifies their SHA-256; `practice.sh` starts the server and opens the page. Model files are not in git. |

## Non-functional requirements

| ID | Requirement |
|----|-------------|
| NFR-RC-01 | **Offline at runtime**: no network access after setup; server bound to `127.0.0.1`; page has no external scripts, fonts or URLs. |
| NFR-RC-02 | Feedback for a ≤ 30 s recording in ≤ 5 s on the author's Mac (model alone ~0.03× real time). |
| NFR-RC-03 | Deterministic: same recording + same model + same settings ⇒ identical findings. |
| NFR-RC-04 | Recordings and history stay on the machine, in a git-ignored data folder; nothing is uploaded. |
| NFR-RC-05 | Library + thin CLI/server; Python 3.12, uv, mypy strict, ruff (constitution). No PyTorch/NeMo — `onnxruntime` + numpy. |

## Acceptance criteria

| ID | Given / When / Then | Covers |
|----|---------------------|--------|
| AC-RC-01 | Chapter 1 config → 47 slokas listed with Devanagari + IAST; sloka 2 starts with `सञ्जय उवाच`; sloka 21 has `अर्जुन उवाच` between its halves; removing one MP3 → that sloka shown unavailable. | FR-RC-01 |
| AC-RC-02 | Two learners created; an attempt by A is not visible to B; deleting A removes A's folder only. | FR-RC-02, 11 |
| AC-RC-03 | Normalisation: `पुत्राणाम् आचार्य` ≡ `पुत्राणामाचार्य`; `उपसङ्गम्य` ≡ `उपसङ्गंय`; `सङ्ग` ≡ `संग`; `पश्यामिि` ≡ `पश्यामि`; expected text with or without `धृतराष्ट्र उवाच` matches a transcript without it. | FR-RC-05 |
| AC-RC-04 | Text-level comparison (no audio): expected `समवेतायुयुत्सवः`, heard `समवेतयुरयुत्सव` → findings: vowel length on *samavetā*, extra letter र in *yuyutsavaḥ*, visarga (unsure). Expected `पाण्डव`, heard `पाण्दव` → retroflex ↔ dental on *pāṇḍava*. | FR-RC-06, 07, 08 |
| AC-RC-05 | *(needs the git-ignored takes; skipped if absent)* `audio-input-test/` takes of sloka 1: line 1 has no reported finding in any take; each take has ≥ 1 reported finding in each of lines 2–4; the findings include the confirmed ones (test: त→द in *samavetā*, ā→a in *pāṇḍavāś*; take 1: ड→द in *pāṇḍava*; take 3: त→क in *kimakurvata*). The held final *ā* of *sañjayā* is accepted as chanting (FR-RC-09), so the test take's line 4 has no reported finding. | FR-RC-04–08 |
| AC-RC-06 | *(skipped if teacher audio absent)* Teacher sloka audio of all 47 slokas checked against their own text → average ≤ 1 reported (non-unsure) finding per sloka. | FR-RC-05, 08, NFR quality |
| AC-RC-07 | A finding listed in the accepted-variants file is not reported; marking a finding acceptable on the page adds exactly that equivalence. | FR-RC-09 |
| AC-RC-08 | Word playback: for a finding on *pāṇḍava*, the learner clip and teacher clip each start within 0.2 s of that word in their recordings. | FR-RC-10 |
| AC-RC-09 | `recite-check "take 1 - fail.mp3" --sloka 1 --json` → valid JSON with the same findings as the page; exit 1. A correct teacher recording → exit 0. | FR-RC-12 |
| AC-RC-10 | With network blocked after setup, practice and CLI work; the served page contains no `http://`/`https://` URL except `127.0.0.1`. | NFR-RC-01 |
| AC-RC-11 | Same WAV submitted twice → identical findings JSON. | NFR-RC-03 |
| AC-RC-12 | `recite-setup` with a corrupted model file → checksum error, exit 2; with correct files → no download on the second run. | FR-RC-13 |

## Phase 2 (after acceptance by the family)

- More users / devices: other machines or phones on the home network; per-learner settings.
- Melody / chanting-tune and rhythm feedback (pitch contour vs teacher; laghu/guru timing).
- Vowel-length checks by duration (in addition to the letters the model hears).
- More chapters (needs teacher recordings); automatic chapter setup from the feature 001–003 outputs.
- Practice plans: suggest the slokas or sounds to repeat, based on history.
- Optional richer feedback wording; anything online only if explicitly accepted (constitution 12).
- Before sharing outside the family: an explicit licence from the model author.

## Known limits

- The model is weak on visarga; those findings stay *unsure* (FR-RC-08).
- About one wrong letter every 2–3 lines on correct recitation; the confidence rule (FR-RC-08) and accepted variants
  (FR-RC-09) are the guard against false alarms — AC-RC-06 measures it.
- Feedback is about the letters the model hears; it does not judge melody, and judges vowel length only through the
  letters it outputs (ā vs a), not by measured duration (Phase 2).
- Related fix outside this feature: the splitter puts sloka 1's spoken `धृतराष्ट्र उवाच` into the intro audio while
  the text attaches it to sloka 1; FR-RC-05 tolerates either.
