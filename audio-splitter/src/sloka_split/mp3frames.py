"""Find the audio frames of an MP3 file so it can be cut without re-encoding (FR-AS-06).

Tags (ID3v2, ID3v1, APE) and the Xing/Info/VBRI header frame are not audio and are left out.
"""

from __future__ import annotations

from dataclasses import dataclass

_BITRATES_KBPS = {
    # (mpeg1?, index) -> kbps, Layer III only
    True: [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0],
    False: [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0],
}
_SAMPLE_RATES = {3: [44100, 48000, 32000], 2: [22050, 24000, 16000], 0: [11025, 12000, 8000]}  # version bits


class Mp3Error(ValueError):
    """The file is not an MP3 this tool can cut."""


@dataclass(frozen=True)
class FrameHeader:
    size: int
    sample_rate: int
    samples: int  # samples per channel in this frame
    mpeg1: bool
    mono: bool
    crc: bool


@dataclass(frozen=True)
class Mp3Audio:
    """Audio frames of one MP3 file: frame i is data[offsets[i] : offsets[i] + sizes[i]]."""

    data: bytes
    offsets: list[int]
    sizes: list[int]
    sample_rate: int
    samples_per_frame: int

    @property
    def frame_count(self) -> int:
        return len(self.offsets)

    @property
    def duration_s(self) -> float:
        return self.frame_count * self.samples_per_frame / self.sample_rate

    def frame_bytes(self, start: int, stop: int) -> bytes:
        """Concatenated bytes of frames [start, stop)."""
        return b"".join(
            self.data[o : o + s] for o, s in zip(self.offsets[start:stop], self.sizes[start:stop], strict=True)
        )

    def audio_bytes(self) -> bytes:
        """All audio frames, without tags or the Xing/Info frame."""
        return self.frame_bytes(0, self.frame_count)

    def frame_at(self, seconds: float) -> int:
        """Index of the frame boundary nearest to a time, clamped to [0, frame_count]."""
        idx = round(seconds * self.sample_rate / self.samples_per_frame)
        return max(0, min(self.frame_count, idx))


def parse_header(h: bytes) -> FrameHeader | None:
    """Decode a 4-byte Layer III frame header; None if it is not one."""
    if len(h) < 4 or h[0] != 0xFF or (h[1] & 0xE0) != 0xE0:
        return None
    version = (h[1] >> 3) & 3  # 3 = MPEG1, 2 = MPEG2, 0 = MPEG2.5, 1 = reserved
    layer = (h[1] >> 1) & 3  # 1 = Layer III
    if version == 1 or layer != 1:
        return None
    br_idx, sr_idx = h[2] >> 4, (h[2] >> 2) & 3
    if br_idx in (0, 15) or sr_idx == 3:  # free-format bitrate is not supported
        return None
    mpeg1 = version == 3
    kbps = _BITRATES_KBPS[mpeg1][br_idx]
    sample_rate = _SAMPLE_RATES[version][sr_idx]
    padding = (h[2] >> 1) & 1
    samples = 1152 if mpeg1 else 576
    size = (samples // 8) * kbps * 1000 // sample_rate + padding
    return FrameHeader(size, sample_rate, samples, mpeg1, (h[3] >> 6) == 3, crc=not (h[1] & 1))


def _id3v2_size(data: bytes) -> int:
    if data[:3] != b"ID3" or len(data) < 10:
        return 0
    s = data[6:10]
    size = (s[0] << 21) | (s[1] << 14) | (s[2] << 7) | s[3]
    footer = 10 if data[5] & 0x10 else 0
    return 10 + size + footer


def _is_info_frame(data: bytes, offset: int, hdr: FrameHeader) -> bool:
    """True for the Xing/Info/VBRI metadata frame LAME and others put first."""
    side = (17 if hdr.mono else 32) if hdr.mpeg1 else (9 if hdr.mono else 17)
    pos = offset + 4 + (2 if hdr.crc else 0) + side
    return data[pos : pos + 4] in (b"Xing", b"Info") or data[offset + 36 : offset + 40] == b"VBRI"


def _valid_at(data: bytes, pos: int) -> FrameHeader | None:
    """Header at pos, accepted only if the next frame (or end of file) follows where expected."""
    hdr = parse_header(data[pos : pos + 4])
    if hdr is None:
        return None
    nxt = pos + hdr.size
    if nxt == len(data) or data[nxt : nxt + 3] == b"TAG" or data[nxt : nxt + 8] == b"APETAGEX":
        return hdr
    return hdr if parse_header(data[nxt : nxt + 4]) is not None else None


def parse(data: bytes) -> Mp3Audio:
    """Locate every audio frame. Junk between frames is skipped (resync on the next valid header)."""
    pos = _id3v2_size(data)
    offsets: list[int] = []
    sizes: list[int] = []
    first: FrameHeader | None = None
    while pos + 4 <= len(data):
        if data[pos : pos + 3] == b"TAG" and len(data) - pos == 128:
            break  # ID3v1
        if data[pos : pos + 8] == b"APETAGEX":
            break
        hdr = _valid_at(data, pos)
        if hdr is None:
            pos += 1
            continue
        if first is None:
            first = hdr
            if _is_info_frame(data, pos, hdr):
                pos += hdr.size
                continue
        elif hdr.sample_rate != first.sample_rate or hdr.samples != first.samples:
            raise Mp3Error(f"sample rate changes at byte {pos}; not supported")
        if pos + hdr.size > len(data):
            break  # truncated last frame
        offsets.append(pos)
        sizes.append(hdr.size)
        pos += hdr.size
    if first is None or not offsets:
        raise Mp3Error("no MPEG Layer III audio frames found")
    return Mp3Audio(data, offsets, sizes, first.sample_rate, first.samples)
