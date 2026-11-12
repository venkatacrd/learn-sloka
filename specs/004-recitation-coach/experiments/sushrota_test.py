"""Option B experiment with Su-śrotā (ONNX int8): does it hear what was said, or what the text says?

1. teacher sloka audio vs its Devanagari text -> character error rate (model noise), confusions by letter
2. learner takes vs sloka-1 text, per line   -> is line 1 clean and lines 2-4 different?

Comparison is on Devanagari code points with spaces, dandas, digits and '-' removed (spacing is unreliable per card).
Usage: python sushrota_test.py <model dir> <audio-outs> <text-outs/slokas> <audio-input-test>
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import miniaudio
import numpy as np
import onnxruntime as ort

model_dir, audio_outs, sloka_txt, takes_dir = (Path(a) for a in sys.argv[1:5])
prep = ort.InferenceSession(str(model_dir / "preprocessor.onnx"), providers=["CPUExecutionProvider"])
asr = ort.InferenceSession(str(model_dir / "sushrota_sanskrit_ctc_int8.onnx"), providers=["CPUExecutionProvider"])
vocab = json.load(open(model_dir / "sanskrit_vocab.json"))


def load(path: Path) -> np.ndarray:
    d = miniaudio.decode_file(str(path), output_format=miniaudio.SampleFormat.FLOAT32, nchannels=1, sample_rate=16000)
    return np.frombuffer(d.samples, dtype=np.float32).copy()


def transcribe(pcm: np.ndarray) -> str:
    feats, flen = prep.run(None, {"audio_signal": pcm[np.newaxis, :], "length": np.array([len(pcm)], dtype=np.int64)})
    logits = asr.run(None, {"audio_signal": feats, "length": flen})[0][0]
    out, prev = [], -1
    for i in np.argmax(logits, axis=-1):
        if i != prev and i != 0:
            out.append(vocab[i])
        prev = i
    return "".join(out).replace("▁", " ").strip()


def norm(s: str) -> str:
    s = unicodedata.normalize("NFC", s)
    return re.sub(r"[\s।॥|\-0-9०-९.,'ऽ]", "", s)


def align(ref: str, hyp: str) -> list[tuple[str, str]]:
    """Levenshtein alignment on code points: list of (ref char or '', hyp char or '')."""
    n, m = len(ref), len(hyp)
    D = np.zeros((n + 1, m + 1), dtype=np.int32)
    D[:, 0] = np.arange(n + 1)
    D[0, :] = np.arange(m + 1)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            D[i, j] = min(D[i - 1, j] + 1, D[i, j - 1] + 1, D[i - 1, j - 1] + (ref[i - 1] != hyp[j - 1]))
    i, j, path = n, m, []
    while i or j:
        if i and j and D[i, j] == D[i - 1, j - 1] + (ref[i - 1] != hyp[j - 1]):
            path.append((ref[i - 1], hyp[j - 1]))
            i, j = i - 1, j - 1
        elif i and D[i, j] == D[i - 1, j] + 1:
            path.append((ref[i - 1], ""))
            i -= 1
        else:
            path.append(("", hyp[j - 1]))
            j -= 1
    return path[::-1]


def cer(path: list[tuple[str, str]]) -> tuple[int, int]:
    errs = sum(1 for r, h in path if r != h)
    return errs, sum(1 for r, _ in path if r)


_DEV: dict[int, list[str]] = {}


def _load_dev() -> None:
    """Devanagari lines per verse from the converter's JSONL (speaker line attached to the next verse)."""
    jsonl = next(sloka_txt.parent.glob("*.romanized.jsonl"))
    speaker: list[str] = []
    for row in jsonl.read_text(encoding="utf-8").splitlines():
        ex = json.loads(row)["extracted"]
        if ex["unit_type"] == "speaker":
            speaker = list(ex["lines"])
            continue
        ref = (ex.get("verse_ref") or {}).get("normalized")
        if ex["unit_type"] == "verse" and ref and ref.isdigit():
            _DEV[int(ref)] = speaker + list(ex["lines"])
        speaker = []


def sloka_lines(n: int) -> list[str]:
    """Devanagari lines of sloka n as recited: speaker line (if any), then each half-verse split into 2 pādas."""
    if not _DEV:
        _load_dev()
    out = []
    for line in _DEV[n]:
        if "उवाच" in line:
            out.append(re.sub(r"\s*-\s*$", "", line))
            continue
        words = re.sub(r"[।॥0-9०-९]+", "", line).split()
        half = (len(words) + 1) // 2
        out += [" ".join(words[:half]), " ".join(words[half:])]
    return out


def show(path: list[tuple[str, str]]) -> str:
    """ref with differences marked as [ref→heard]."""
    s, buf_r, buf_h = [], "", ""
    for r, h in path + [("", "")]:
        if r == h and r:
            if buf_r or buf_h:
                s.append(f"[{buf_r or '∅'}→{buf_h or '∅'}]")
                buf_r = buf_h = ""
            s.append(r)
        elif r or h:
            buf_r += r
            buf_h += h
    if buf_r or buf_h:
        s.append(f"[{buf_r or '∅'}→{buf_h or '∅'}]")
    return "".join(s)


# ---- 1. teacher audio: model noise -------------------------------------------------------------------------------
print("=== 1. teacher's recitation (correct) vs text ===")
tot_e = tot_n = 0
conf: Counter[str] = Counter()
per = []
for mp3 in sorted(audio_outs.glob("*_sloka_*.mp3")):
    n = int(mp3.stem.rsplit("_", 1)[1])
    hyp = norm(transcribe(load(mp3)))
    lines = sloka_lines(n)
    # sloka 1's speaker line sits in the intro audio; let the model decide whether it was spoken
    best = None
    for cand in ([lines, lines[1:]] if "उवाच" in lines[0] else [lines]):
        p = align(norm("".join(cand)), hyp)
        e, t = cer(p)
        if best is None or e / t < best[0] / best[1]:
            best = (e, t, p)
    e, t, p = best
    tot_e, tot_n = tot_e + e, tot_n + t
    per.append((e / t, n))
    for r, h in p:
        if r != h:
            conf[f"{r or '∅'}→{h or '∅'}"] += 1
    if e / t > 0.05:
        print(f"sloka {n:2d}: CER {e / t:5.1%}  {show(p)}")
print(f"\nall 47 slokas: CER {tot_e / tot_n:.1%} ({tot_e} errors / {tot_n} letters); "
      f"slokas with CER 0: {sum(1 for c, _ in per if c == 0)}, ≤2%: {sum(1 for c, _ in per if c <= 0.02)}")
print("most common differences (text→heard):", ", ".join(f"{k} ×{v}" for k, v in conf.most_common(20)))

# ---- 2. learner takes: line by line ------------------------------------------------------------------------------
print("\n=== 2. learner takes vs sloka 1 text (line 1 correct, mistakes in lines 2-4) ===")
lines = sloka_lines(1)
teacher1 = norm(transcribe(load(next(audio_outs.glob("*_sloka_01.mp3")))))
for take in sorted(takes_dir.glob("*.mp3")):
    raw = transcribe(load(take))
    hyp = norm(raw)
    # map each text line to the heard characters through the alignment (with and without the speaker line)
    use = lines[1:] if "उवाच" in lines[0] and norm(lines[0])[:3] not in hyp[:12] else lines
    ref = "".join(norm(l) for l in use)
    p = align(ref, hyp)
    print(f"\n== {take.name}\nheard: {raw}")
    pos, k = 0, 0
    bounds = np.cumsum([len(norm(l)) for l in use])
    chunks: list[list[tuple[str, str]]] = [[] for _ in use]
    for r, h in p:
        idx = min(int(np.searchsorted(bounds, pos, side="right")), len(use) - 1)
        chunks[idx].append((r, h))
        if r:
            pos += 1
    for i, (line, ch) in enumerate(zip(use, chunks, strict=True)):
        e, t = cer(ch)
        mark = "OK " if e == 0 else "DIFF"
        print(f"  line {i + 1} {mark} {e:2d}/{t:<2d}  {show(ch)}")
