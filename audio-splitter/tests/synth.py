"""Synthetic chant: voiced tones separated by pauses, ending high (pāda continues) or low (cadence)."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

HIGH, LOW, BASE = 165.0, 125.0, 155.0
GAP, SHORT, LONG = 0.5, 0.42, 0.6  # pauses: other, after lines 1/3, after lines 2/4
BREATH = 0.3  # pause inside a line broken by a breath


@dataclass
class Chant:
    pcm: np.ndarray
    sample_rate: int
    gaps: list[tuple[float, float]] = field(default_factory=list)  # every pause (start, end)
    sloka_spans: list[tuple[float, float]] = field(default_factory=list)  # first voice start, last voice end


def _tone(sr: int, dur: float, end_hz: float) -> np.ndarray:
    n = int(dur * sr)
    glide = min(0.6, dur / 2)
    f = np.full(n, BASE)
    g = int(glide * sr)
    f[n - g :] = np.linspace(BASE, end_hz, g)
    phase = 2 * np.pi * np.cumsum(f) / sr
    wave = sum(np.sin(k * phase) / k for k in (1, 2, 3))
    env = np.minimum(1.0, np.minimum(np.arange(n), np.arange(n)[::-1]) / (0.03 * sr))
    return (0.25 * wave * env).astype(np.float32)


def chant(
    sr: int = 16000,
    *,
    intro: int = 2,
    slokas: int = 5,
    speaker_before: int | None = 3,
    closing: int = 2,
    split_pada: tuple[int, int] | None = None,
    monotone: bool = False,
    style: str = "cadence",
) -> Chant:
    """Intro segments, `slokas` × 4 lines, optional speaker segment and split line, closing.

    style "cadence": lines end H L H L (the falling line ends the half-verse);
    style "next":    lines end L H L H (falling pitch on lines 1 and 3, like the reference recording).
    Either way the pause after lines 2 and 4 (half-verse ends) is longer than after lines 1 and 3.
    """
    endings = (HIGH, LOW, HIGH, LOW) if style == "cadence" else (LOW, HIGH, LOW, HIGH)
    pieces: list[tuple[float, float, int, float]] = []  # (duration, end pitch, sloka number or 0, pause after)
    pieces += [(2.0, HIGH, 0, GAP)] * intro
    for s in range(1, slokas + 1):
        if s == speaker_before:
            pieces.append((1.0, HIGH, s, GAP))
        for p, end in enumerate(endings):
            pitch = HIGH if monotone else end
            pause = LONG if p % 2 else SHORT
            if split_pada == (s, p):
                pieces += [(1.5, BASE, s, BREATH), (1.5, pitch, s, pause)]
            else:
                pieces.append((3.0, pitch, s, pause))
    pieces += [(2.0, HIGH, 0, GAP)] * closing

    out = [np.zeros(int(GAP * sr), np.float32)]
    t = GAP
    result = Chant(np.zeros(0, np.float32), sr)
    spans: dict[int, list[float]] = {}
    for i, (dur, pitch, s, pause) in enumerate(pieces):
        out.append(_tone(sr, dur, pitch))
        if s:
            spans.setdefault(s, [t, t])[1] = t + dur
        t += dur
        if i + 1 < len(pieces):
            result.gaps.append((t, t + pause))
            out.append(np.zeros(int(pause * sr), np.float32))
            t += pause
    out.append(np.zeros(int(1.0 * sr), np.float32))
    result.pcm = np.concatenate(out)
    result.sloka_spans = [tuple(spans[s]) for s in sorted(spans)]  # type: ignore[misc]
    return result


def to_mp3(c: Chant, bitrate: int = 128) -> bytes:
    import lameenc

    enc = lameenc.Encoder()
    enc.set_bit_rate(bitrate)
    enc.set_in_sample_rate(c.sample_rate)
    enc.set_channels(1)
    enc.set_quality(2)
    pcm16 = (np.clip(c.pcm, -1, 1) * 32767).astype("<i2").tobytes()
    return with_info_frame(bytes(enc.encode(pcm16) + enc.flush()))


def with_info_frame(mp3: bytes) -> bytes:
    """Prepend a LAME-style 'Info' header frame (lameenc's streaming encoder does not write one)."""
    from sloka_split.mp3frames import parse_header

    hdr = parse_header(mp3[:4])
    assert hdr is not None and hdr.mpeg1 and not hdr.crc
    frame = bytearray(hdr.size)
    frame[:4] = mp3[:4]
    side = 17 if hdr.mono else 32
    frame[4 + side : 8 + side] = b"Info"
    return bytes(frame) + mp3
