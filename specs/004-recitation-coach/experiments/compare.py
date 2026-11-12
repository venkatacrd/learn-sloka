"""Run the option A detector: each learner take vs the teacher's sloka; show flags with the text around them."""
import os
import re
import sys
from pathlib import Path

import librosa
import numpy as np

os.environ["LOCAL_TEMPO"] = "1"
sloka = int(sys.argv[1])
sys.argv = [sys.argv[0], "audio-outs", "audio-splitter/src"]
sys.path.insert(0, str(Path(__file__).parent))
import option_a  # noqa: E402
from option_a import SR, detect, find_segments, load  # noqa: E402

option_a.LOCAL_TEMPO = True
teacher = load(next(Path("audio-outs").glob(f"*_sloka_{sloka:02d}.mp3")))
text = next(Path("text-outs/slokas").glob(f"*_{sloka:02d}.txt")).read_text(encoding="utf-8")
iast = [l for l in text.split("\n\n", 1)[1].splitlines() if l.strip()] if "\n\n" in text else text.splitlines()
# lines as recited: speaker line, then each half-verse split into its two pādas at the word midpoint
padas: list[str] = []
for line in iast:
    words = re.sub(r"[|0-9]+", "", line).split()
    if "uvāca" in line:
        padas.append(" ".join(words))
    else:
        half = (len(words) + 1) // 2
        padas += [" ".join(words[:half]), " ".join(words[half:])]
segs = find_segments(teacher, SR)
if len(padas) == len(segs) + 1 and "uvāca" in padas[0]:
    padas = padas[1:]  # the splitter put this speaker line in the intro audio, not in the sloka file
print(f"teacher sloka {sloka}: {len(segs)} voice segments; text lines: {padas}")


def where(t: float) -> str:
    for i, (a, b) in enumerate(segs):
        if a - 0.15 <= t <= b + 0.15:
            words = padas[i].split() if i < len(padas) else []
            if not words:
                return f"segment {i + 1}"
            k = min(len(words) - 1, int((t - a) / max(b - a, 1e-3) * len(words)))
            return f"line {i + 1} ≈ '{words[max(k, 0)]}'"
    return "in a pause"


def level(pcm):
    db = 20 * np.log10(librosa.feature.rms(y=pcm, frame_length=512, hop_length=160)[0] + 1e-9)
    return np.percentile(db, 5), np.percentile(db, 50), np.percentile(db, 95)


print("teacher levels (dB, 5/50/95 pct): %.0f / %.0f / %.0f" % level(teacher))
for take in sorted(Path("audio-input-test").glob("*.mp3")):
    pcm = load(take)
    print(f"\n== {take.name}  ({len(pcm)/SR:.1f}s vs teacher {len(teacher)/SR:.1f}s)  levels %.0f / %.0f / %.0f" % level(pcm))
    r = detect(teacher, pcm)
    # where each teacher line landed in the learner take
    path = r.path
    for i, (a, b) in enumerate(segs):
        sel = path[(path[:, 0] * 160 / SR >= a) & (path[:, 0] * 160 / SR <= b)]
        la, lb = sel[:, 1].min() * 160 / SR, sel[:, 1].max() * 160 / SR
        print(f"  line {i + 1} '{padas[i] if i < len(padas) else '?'}': teacher {a:4.1f}-{b:4.1f}s ({b - a:.1f}s)"
              f" -> learner {la:4.1f}-{lb:4.1f}s ({lb - la:.1f}s)")
    # extra material in the learner take: learner stretches where the teacher position barely moves
    vl = option_a.voiced_mask(pcm)[: path[:, 1].max() + 1]
    tpos = np.zeros(path[:, 1].max() + 1)
    cnt = np.zeros_like(tpos)
    for ti, li in path:
        tpos[li] += ti
        cnt[li] += 1
    tpos /= np.maximum(cnt, 1)
    sl = np.gradient(np.convolve(tpos, np.ones(25) / 25, "same"))
    rate = np.median(sl[vl & (sl > 0)])
    for a, b in option_a.runs((sl < 0.25 * rate) & vl, 40):
        t = tpos[(a + b) // 2] * 160 / SR
        r.flags.append(("EXTRA in learner", t, t))
        print(f"  EXTRA in learner     learner {a * 160 / SR:5.1f}-{b * 160 / SR:5.1f}s ({(b - a) / 100:.1f}s) near teacher {t:.1f}s -> {where(t)}")
    for kind, a, b in r.flags:
        if kind.startswith("EXTRA"):
            continue
        print(f"  {kind:20s} teacher {a:5.1f}-{b:5.1f}s  -> {where((a + b) / 2)}")
    if not r.flags:
        print("  no flags")
