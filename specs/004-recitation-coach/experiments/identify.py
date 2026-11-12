"""Which teacher sloka does each learner take match best? (normalised DTW cost over all 47)"""
import sys
from pathlib import Path

import librosa
import numpy as np

sys.argv = [sys.argv[0], "audio-outs", "audio-splitter/src"] + sys.argv[1:]
sys.path.insert(0, str(Path(__file__).parent))
from option_a import features, load, find_segments, SR  # noqa: E402

teachers = {int(p.stem.rsplit("_", 1)[1]): features(load(p)) for p in sorted(Path("audio-outs").glob("*_sloka_*.mp3"))}
for take in sorted(Path("audio-input-test").glob("*.mp3")):
    pcm = load(take)
    L = features(pcm)
    lines = find_segments(pcm, SR)
    scores = []
    for n, T in teachers.items():
        D, wp = librosa.sequence.dtw(X=T, Y=L, metric="cosine", subseq=False)
        scores.append((D[-1, -1] / len(wp), n))
    scores.sort()
    best = ", ".join(f"sloka {n} ({s:.3f})" for s, n in scores[:4])
    print(f"{take.name}: {len(lines)} voice segments, {len(pcm)/SR:.1f}s -> best: {best}; median of all {np.median([s for s,_ in scores]):.3f}")
