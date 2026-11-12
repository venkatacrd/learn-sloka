"""Option A de-risking experiment: compare a 'learner' recording with the teacher's, find differences.

No learner recordings exist yet, so a learner is simulated from the teacher's sloka:
  different voice  = pitch +3 semitones, a different 'microphone' (filter), background noise,
  different tempo  = every line stretched by a random 0.82-1.22x, every pause scaled 0.6-1.6x,
  planted mistakes = (a) a ~0.7 s chunk cut out of one line (skipped word),
                     (b) the steadiest 0.3-0.45 s voiced stretch of another line squeezed to half (short vowel).
A 'control' take gets the same voice/tempo treatment but no mistakes -> any flag there is a false alarm.

Detector (option A): MFCC fingerprints (speaker-normalised), dynamic time warping, then
  - sound mismatch: stretches where aligned fingerprints stay unusually far apart
  - duration:       stretches the alignment had to squeeze to < 60 % of the learner's own average tempo
Pauses are excluded (pause length is free).

Usage: python option_a.py <audio-outs dir> <audio-splitter/src> <sloka numbers...>
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import librosa
import miniaudio
import numpy as np
import scipy.signal

SR = 16000
import os
LOCAL_TEMPO = os.environ.get("LOCAL_TEMPO") == "1"
HOP = 160  # 10 ms
sys.path.insert(0, sys.argv[2])
from sloka_split.analysis import find_segments  # noqa: E402  (voice segments ≈ lines)


def load(path: Path) -> np.ndarray:
    d = miniaudio.decode_file(str(path), output_format=miniaudio.SampleFormat.FLOAT32, nchannels=1, sample_rate=SR)
    return np.frombuffer(d.samples, dtype=np.float32).copy()


# ----------------------------------------------------------------------------------------------- simulation


@dataclass
class Piece:
    t0: float  # teacher time span
    t1: float
    kind: str  # line | pause | skip | squeeze
    l0: float = 0.0  # learner time span (filled in)
    l1: float = 0.0


@dataclass
class Learner:
    pcm: np.ndarray
    pieces: list[Piece]
    planted: list[tuple[str, float, float]] = field(default_factory=list)  # (kind, teacher t0, t1)


def steadiest(pcm: np.ndarray, a: float, b: float) -> tuple[float, float]:
    """Most spectrally stable, loud 0.36 s inside [a, b] (a held vowel)."""
    seg = pcm[int(a * SR) : int(b * SR)]
    S = np.abs(librosa.stft(seg, n_fft=512, hop_length=HOP))
    flux = np.r_[0, np.sqrt((np.diff(np.log1p(S), axis=1) ** 2).sum(0))]
    rms = librosa.feature.rms(S=S, frame_length=512, hop_length=HOP)[0]
    w = 36
    score = np.convolve(flux, np.ones(w), "valid") / w - 0.5 * np.convolve(np.log(rms + 1e-6), np.ones(w), "valid") / w
    lo, hi = 20, len(score) - 20  # keep away from line edges
    k = lo + int(np.argmin(score[lo:hi]))
    return a + k * HOP / SR, a + (k + w) * HOP / SR


def simulate(teacher: np.ndarray, rng: np.random.Generator, mistakes: bool) -> Learner:
    lines = find_segments(teacher, SR)
    planted: list[tuple[str, float, float]] = []
    pieces: list[Piece] = []
    long_lines = [i for i, (a, b) in enumerate(lines) if b - a > 2.2]
    skip_line, squeeze_line = (rng.choice(long_lines, 2, replace=False) if mistakes else (-1, -1))
    t = 0.0
    for i, (a, b) in enumerate(lines):
        if a > t:
            pieces.append(Piece(t, a, "pause"))
        if i == skip_line:
            c0 = a + 0.35 * (b - a)
            c1 = c0 + 0.7
            pieces += [Piece(a, c0, "line"), Piece(c0, c1, "skip"), Piece(c1, b, "line")]
            planted.append(("skipped word", c0, c1))
        elif i == squeeze_line:
            v0, v1 = steadiest(teacher, a, b)
            pieces += [Piece(a, v0, "line"), Piece(v0, v1, "squeeze"), Piece(v1, b, "line")]
            planted.append(("short vowel", v0, v1))
        else:
            pieces.append(Piece(a, b, "line"))
        t = b
    if t < len(teacher) / SR:
        pieces.append(Piece(t, len(teacher) / SR, "pause"))

    out: list[np.ndarray] = []
    pos = 0.0
    line_rate = {}  # one tempo per line
    for p in pieces:
        x = teacher[int(p.t0 * SR) : int(p.t1 * SR)]
        if p.kind == "skip":
            y = x[:0]
        elif p.kind == "pause":
            y = np.zeros(int(len(x) * rng.uniform(0.6, 1.6)), np.float32)
        else:
            key = round(p.t0, 1) if p.kind == "line" else None
            rate = line_rate.setdefault(key, rng.uniform(0.82, 1.22)) if key is not None else 2.0
            y = librosa.effects.time_stretch(x, rate=rate) if len(x) > 2048 else x
        p.l0, p.l1 = pos, pos + len(y) / SR
        pos = p.l1
        out.append(y.astype(np.float32))
    pcm = np.concatenate(out)
    pcm = librosa.effects.pitch_shift(pcm, sr=SR, n_steps=3)  # different voice
    b, a = scipy.signal.butter(2, [150, 5000], btype="band", fs=SR)  # different microphone
    pcm = scipy.signal.lfilter(b, a, pcm).astype(np.float32)
    noise = rng.normal(0, 1, len(pcm)).astype(np.float32)
    pcm = pcm + noise * np.sqrt(np.mean(pcm**2) / 10 ** (30 / 10))  # 30 dB SNR
    return Learner(pcm, pieces, planted)


def true_map(pieces: list[Piece], t: float) -> float | None:
    """Teacher time -> learner time for kept speech (None inside cut/squeezed/pauses)."""
    for p in pieces:
        if p.t0 <= t < p.t1 and p.kind == "line":
            return p.l0 + (t - p.t0) / (p.t1 - p.t0) * (p.l1 - p.l0)
    return None


# ----------------------------------------------------------------------------------------------- detector


def features(pcm: np.ndarray) -> np.ndarray:
    m = librosa.feature.mfcc(y=pcm, sr=SR, n_mfcc=20, n_fft=512, hop_length=HOP, n_mels=40)[1:]  # drop energy
    m = (m - m.mean(1, keepdims=True)) / (m.std(1, keepdims=True) + 1e-8)  # per-speaker normalisation
    d = librosa.feature.delta(m)
    return np.vstack([m, d])


def voiced_mask(pcm: np.ndarray) -> np.ndarray:
    rms = librosa.feature.rms(y=pcm, frame_length=512, hop_length=HOP)[0]
    db = 20 * np.log10(rms + 1e-9)
    return db > np.median(db[db > -70]) - 20


def runs(mask: np.ndarray, min_len: int) -> list[tuple[int, int]]:
    out, i = [], 0
    while i < len(mask):
        if mask[i]:
            j = i
            while j < len(mask) and mask[j]:
                j += 1
            if j - i >= min_len:
                out.append((i, j))
            i = j
        else:
            i += 1
    return out


@dataclass
class Result:
    flags: list[tuple[str, float, float]]  # (kind, teacher t0, t1)
    path: np.ndarray  # (teacher frame, learner frame) pairs, ascending


def detect(teacher: np.ndarray, learner: np.ndarray) -> Result:
    T, L = features(teacher), features(learner)
    _, wp = librosa.sequence.dtw(X=T, Y=L, metric="cosine")
    wp = wp[::-1]
    n = T.shape[1]
    vt = voiced_mask(teacher)[:n]

    # learner position for each teacher frame (mean over the path)
    lpos = np.zeros(n)
    cost = np.zeros(n)
    cnt = np.zeros(n)
    Tn = T / (np.linalg.norm(T, axis=0, keepdims=True) + 1e-9)
    Ln = L / (np.linalg.norm(L, axis=0, keepdims=True) + 1e-9)
    for ti, li in wp:
        lpos[ti] += li
        cost[ti] += 1 - float(Tn[:, ti] @ Ln[:, li])
        cnt[ti] += 1
    lpos /= np.maximum(cnt, 1)
    cost /= np.maximum(cnt, 1)
    cost_s = np.convolve(cost, np.ones(20) / 20, "same")

    flags: list[tuple[str, float, float]] = []
    # sound mismatch: robust outliers of the alignment cost, voiced teacher frames only
    vals = cost_s[vt]
    thr = np.median(vals) + 4 * np.median(np.abs(vals - np.median(vals)))
    for a, b in runs((cost_s > thr) & vt, 15):
        flags.append(("sound differs", a * HOP / SR, b * HOP / SR))
    # duration: local tempo (learner frames per teacher frame) vs the learner's own average, voiced only
    w = 25
    slope = np.gradient(np.convolve(lpos, np.ones(w) / w, "same"))
    if LOCAL_TEMPO:
        # v2: compare with the tempo of the surrounding ±1.5 s of speech, and skip 100 ms around pause edges
        local = np.array(
            [np.median(slope[max(0, i - 150) : i + 150][vt[max(0, i - 150) : i + 150]] if vt[max(0, i - 150) : i + 150].any() else [1.0]) for i in range(n)]
        )
        edge = np.convolve((~vt).astype(float), np.ones(21), "same") > 0
        short = (slope < 0.6 * local) & vt & ~edge
    else:
        speech_rate = np.median(slope[vt & (slope > 0)])
        short = (slope < 0.6 * speech_rate) & vt
    for a, b in runs(short, 15):
        flags.append(("too short / missing", a * HOP / SR, b * HOP / SR))
    return Result(sorted(flags, key=lambda f: f[1]), np.array(wp))


# ----------------------------------------------------------------------------------------------- evaluation


def overlap(a0: float, a1: float, b0: float, b1: float, pad: float = 0.15) -> bool:
    return a0 < b1 + pad and b0 < a1 + pad


def alignment_error(res: Result, sim: Learner, teacher_len: int) -> np.ndarray:
    errs = []
    lpos: dict[int, list[int]] = {}
    for ti, li in res.path:
        lpos.setdefault(int(ti), []).append(int(li))
    for ti in range(0, teacher_len, 5):
        true = true_map(sim.pieces, ti * HOP / SR)
        if true is not None and ti in lpos:
            errs.append(abs(np.mean(lpos[ti]) * HOP / SR - true))
    return np.array(errs)


def main() -> None:
    outs, numbers = Path(sys.argv[1]), [int(x) for x in sys.argv[3:]]
    rng = np.random.default_rng(7)
    tot = {"control_takes": 0, "false_flags_control": 0, "planted": 0, "caught": 0, "false_flags_mistake": 0}
    by_kind: dict[str, list[int]] = {}
    align: list[np.ndarray] = []
    for n in numbers:
        teacher = load(next(outs.glob(f"*_sloka_{n:02d}.mp3")))
        nT = features(teacher).shape[1]
        for take in range(2):
            ctrl = simulate(teacher, rng, mistakes=False)
            r = detect(teacher, ctrl.pcm)
            align.append(alignment_error(r, ctrl, nT))
            tot["control_takes"] += 1
            tot["false_flags_control"] += len(r.flags)
            fl = ", ".join(f"{k} {a:.1f}-{b:.1f}s" for k, a, b in r.flags) or "none"
            print(f"sloka {n:2d} control {take + 1}: flags: {fl}")

            mis = simulate(teacher, rng, mistakes=True)
            r = detect(teacher, mis.pcm)
            align.append(alignment_error(r, mis, nT))
            used = set()
            for kind, a, b in mis.planted:
                hit = [i for i, (_, f0, f1) in enumerate(r.flags) if overlap(a, b, f0, f1)]
                used.update(hit)
                by_kind.setdefault(kind, []).append(1 if hit else 0)
                tot["planted"] += 1
                tot["caught"] += bool(hit)
                how = ", ".join(r.flags[i][0] for i in hit) or "MISSED"
                print(f"sloka {n:2d} mistake {take + 1}: planted {kind} at {a:.1f}-{b:.1f}s -> {how}")
            extra = [f for i, f in enumerate(r.flags) if i not in used]
            tot["false_flags_mistake"] += len(extra)
            if extra:
                print(f"            other flags: " + ", ".join(f"{k} {a:.1f}-{b:.1f}s" for k, a, b in extra))

    e = np.concatenate(align)
    print("\n=== summary ===")
    print(f"alignment error on kept speech: median {np.median(e) * 1000:.0f} ms, 90th pct {np.percentile(e, 90) * 1000:.0f} ms")
    print(f"false flags on correct (control) takes: {tot['false_flags_control']} in {tot['control_takes']} takes "
          f"= {tot['false_flags_control'] / tot['control_takes']:.2f} per sloka")
    for kind, hits in by_kind.items():
        print(f"caught {kind}: {sum(hits)}/{len(hits)}")
    print(f"extra flags on takes with mistakes: {tot['false_flags_mistake']} in {tot['control_takes']} takes")


if __name__ == "__main__":
    main()
