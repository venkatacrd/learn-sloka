# 003 – Audio Splitter: Technical Plan

Implements [spec.md](spec.md).

## Stack

| Concern | Choice | Why |
|---------|--------|-----|
| Decode for analysis | **miniaudio** (wheel bundles dr_mp3) | No ffmpeg/system binary needed (NFR-AS-03); decodes + resamples to 16 kHz mono in ~1 s |
| Signal math | **numpy** | RMS, FFT autocorrelation pitch |
| Cutting | own MP3 frame parser (`mp3frames.py`) | Lossless, byte-exact (FR-AS-06, NFR-AS-01) |
| Tags | **mutagen** | Well-tested ID3 writer |
| CLI | **typer** | Same as 001/002 |
| Tests only | **lameenc** | Encode synthetic chants to MP3 in tests |

## Layout

```
audio-splitter/
  src/sloka_split/
    mp3frames.py   # parse frames, skip tags & Xing/Info/VBRI, slice by frame range     (FR-AS-06)
    analysis.py    # segments, tail pitch, cadence threshold, sloka grouping, cut times   (FR-AS-02..05)
    splitter.py    # files in/out, names, tags, reports, coverage check, clean           (FR-AS-01, 07..11)
    cli.py         # thin typer CLI                                                      (FR-AS-12)
  tests/  synth.py (synthetic chant generator) + test_*.py
split-audio.sh     # (repo root) clean + split into audio-outs/                           (FR-AS-13)
```

## Flow per file

```
mp3 bytes ─► mp3frames.parse ─► frame list (offset, size, samples)
         └► miniaudio decode 16 kHz mono ─► analysis.analyze(pcm)
                 RMS dB ─► segments ─► tail pitch ─► Otsu ─► cadences ─► slokas ─► cut times (s)
cut times ─► frame indices ─► parts ─► write frames + ID3 ─► splits.json, labels.txt ─► coverage check
```

Time ↔ frame: `frame = round(t * sample_rate / samples_per_frame)` over audio frames only (Xing frame excluded).
