"""Su-śrotā Sanskrit ASR (ONNX INT8): pinned download, checksum, transcription with times (FR-RC-04, 13).

Model: https://huggingface.co/gnumanth/sushrota-sanskrit-asr-onnx (ONNX export of prathoshap/sushrota-sanskrit-asr,
Prof. Prathosh A P, IISc Bengaluru). Personal/family use; see specs/004-recitation-coach/brainstorm.md › Licence.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import miniaudio
import numpy as np
import numpy.typing as npt

from .compare import HeardChar

REPO = "gnumanth/sushrota-sanskrit-asr-onnx"
REVISION = "d320b7aada7f844b2c78d4f6c935aba77d0327a0"
FILES = {
    "preprocessor.onnx": "aab44917d3d894b2cfa84cffb8ac7ebe04c51540b3f3d565e6a7dc6e2630f859",
    "sushrota_sanskrit_ctc_int8.onnx": "6a52c782ecbc3cfc389eac2832d069677c587b6693c2ca4e68ea7ad7d59f3e64",
    "sanskrit_vocab.json": "be61d707852a6f8965f15a6cf160c00083e6bea03b6de8e474b9573fd7bb2719",
}
DEFAULT_BASE_URL = "https://huggingface.co"
SAMPLE_RATE = 16000
FRAME_S = 0.04  # one CTC output step


class ModelError(RuntimeError):
    """Model files missing or corrupted."""


def home() -> Path:
    return Path(os.environ.get("RECITE_COACH_HOME", Path.home() / ".recite-coach"))


def model_dir() -> Path:
    return home() / "models" / REVISION


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def missing_or_bad() -> list[str]:
    d = model_dir()
    return [name for name, sha in FILES.items() if not (d / name).is_file() or _sha256(d / name) != sha]


def setup(base_url: str = DEFAULT_BASE_URL, log: object = print) -> list[str]:
    """Download the pinned model files that are missing or corrupted; verify every checksum. Returns the files
    downloaded. Raises ModelError when a download does not match its checksum."""
    d = model_dir()
    d.mkdir(parents=True, exist_ok=True)
    fetched = []
    for name in missing_or_bad():
        url = f"{base_url.rstrip('/')}/{REPO}/resolve/{REVISION}/{name}"
        if callable(log):
            log(f"downloading {name} …")
        with tempfile.NamedTemporaryFile(dir=d, delete=False) as tmp:
            try:
                with urllib.request.urlopen(url, timeout=60) as resp:
                    shutil.copyfileobj(resp, tmp)
            except OSError as exc:
                Path(tmp.name).unlink(missing_ok=True)
                raise ModelError(f"cannot download {url}: {exc}") from exc
        if _sha256(Path(tmp.name)) != FILES[name]:
            Path(tmp.name).unlink(missing_ok=True)
            raise ModelError(f"checksum mismatch for {name} (download corrupted or file changed upstream)")
        Path(tmp.name).replace(d / name)
        fetched.append(name)
    return fetched


Pcm = npt.NDArray[np.float32]


def load_audio(path: Path) -> Pcm:
    """Any WAV/MP3/FLAC file -> 16 kHz mono float32."""
    d = miniaudio.decode_file(str(path), output_format=miniaudio.SampleFormat.FLOAT32, nchannels=1,
                              sample_rate=SAMPLE_RATE)  # fmt: skip
    return np.frombuffer(d.samples, dtype=np.float32).copy()


def decode_audio(data: bytes) -> Pcm:
    """Audio file bytes (e.g. the page's WAV) -> 16 kHz mono float32."""
    d = miniaudio.decode(data, output_format=miniaudio.SampleFormat.FLOAT32, nchannels=1, sample_rate=SAMPLE_RATE)
    return np.frombuffer(d.samples, dtype=np.float32).copy()


@dataclass
class Recognizer:
    """Loaded once; transcribe() is thread-safe enough for the single-user local server."""

    prep: object
    asr: object
    vocab: list[str]

    @classmethod
    def load(cls) -> Recognizer:
        bad = missing_or_bad()
        if bad:
            raise ModelError(f"model files missing or corrupted: {', '.join(bad)} — run recite-setup")
        import onnxruntime as ort

        d = model_dir()
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = max(1, (os.cpu_count() or 2) // 2)
        prep = ort.InferenceSession(str(d / "preprocessor.onnx"), opts, providers=["CPUExecutionProvider"])
        asr = ort.InferenceSession(str(d / "sushrota_sanskrit_ctc_int8.onnx"), opts, providers=["CPUExecutionProvider"])
        vocab = json.loads((d / "sanskrit_vocab.json").read_text(encoding="utf-8"))
        return cls(prep, asr, vocab)

    def transcribe(self, pcm: Pcm) -> list[HeardChar]:
        """Greedy CTC; every output character keeps its token's time span and probability."""
        if len(pcm) < SAMPLE_RATE // 10:
            return []
        feats, flen = self.prep.run(  # type: ignore[attr-defined]
            None, {"audio_signal": pcm[np.newaxis, :].astype(np.float32), "length": np.array([len(pcm)], np.int64)}
        )
        logits = self.asr.run(None, {"audio_signal": feats, "length": flen})[0][0]  # type: ignore[attr-defined]
        z = logits - logits.max(axis=-1, keepdims=True)
        probs = np.exp(z) / np.exp(z).sum(axis=-1, keepdims=True)
        ids = probs.argmax(axis=-1)
        out: list[HeardChar] = []
        k = 0
        while k < len(ids):
            tok = int(ids[k])
            j = k
            while j < len(ids) and ids[j] == tok:
                j += 1
            if tok != 0:
                p = float(probs[k:j, tok].max())
                piece = self.vocab[tok].replace("▁", " ")
                for ch in piece:
                    out.append(HeardChar(ch, round(k * FRAME_S, 3), round(j * FRAME_S, 3), round(p, 4)))
            k = j
        return out
