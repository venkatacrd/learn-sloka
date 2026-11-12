# Feature 004 experiments (2026-11-10/11)

Throw-away research scripts, kept so the measurements in `../brainstorm.md` can be re-run. Not part of any project;
not linted or tested. Run from the repo root with a Python env that has the listed packages.

| Script | What it measures | Needs |
|---|---|---|
| `option_a.py` | Option A (MFCC + DTW vs teacher) on simulated learners with planted mistakes | numpy, miniaudio, librosa, scipy; `audio-splitter/src` on the path |
| `identify.py` | which teacher sloka each learner take matches best | as above |
| `compare.py` | option A on real takes, line by line, incl. "extra" material | as above |
| `sushrota_test.py` | Option B with Su-śrotā ONNX: teacher CER over all slokas + learner takes line by line | numpy, miniaudio, onnxruntime; model files from `gnumanth/sushrota-sanskrit-asr-onnx` |

```sh
python option_a.py audio-outs audio-splitter/src 3 5 10 17 30          # LOCAL_TEMPO=1 for v2
python sushrota_test.py <model-dir> audio-outs text-outs/slokas audio-input-test
```

`compare.py` and `identify.py` import `option_a.py` from the same folder and expect the learner takes in
`audio-input-test/` (git-ignored). `sushrota_test.py` reads the Devanagari text from `text-outs/*.romanized.jsonl`.
