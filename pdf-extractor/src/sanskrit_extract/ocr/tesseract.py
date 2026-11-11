"""Local Tesseract engine via pytesseract (FR-EX-04). Offline only; results cached on disk."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from sanskrit_extract.ocr.base import OcrLine


class TesseractEngine:
    name = "tesseract"

    def __init__(self, languages: str = "san+hin", psm: int = 6, cache_dir: Path | None = None) -> None:
        self.languages = languages
        self.psm = psm
        self.cache_dir = cache_dir

    def version(self) -> str:
        import pytesseract

        return str(pytesseract.get_tesseract_version())

    def _cache_path(self, png: bytes, dpi: int) -> Path | None:
        if self.cache_dir is None:
            return None
        key = hashlib.sha256(png + f"|{self.version()}|{self.languages}|{self.psm}|{dpi}".encode()).hexdigest()
        return self.cache_dir / f"{key}.json"

    def ocr(self, png: bytes, dpi: int) -> list[OcrLine]:
        cache = self._cache_path(png, dpi)
        if cache is not None and cache.exists():
            return [OcrLine(d["text"], d["confidence"], tuple(d["bbox"])) for d in json.loads(cache.read_text())]
        lines = self._run(png, dpi)
        if cache is not None:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(
                json.dumps(
                    [{"text": x.text, "confidence": x.confidence, "bbox": list(x.bbox)} for x in lines],
                    ensure_ascii=False,
                )
            )
        return lines

    def _run(self, png: bytes, dpi: int) -> list[OcrLine]:
        import pytesseract

        from sanskrit_extract.ocr.preprocess import preprocess

        image = preprocess(png)
        data = pytesseract.image_to_data(
            image, lang=self.languages, config=f"--psm {self.psm}", output_type=pytesseract.Output.DICT
        )
        scale = 72.0 / dpi
        groups: dict[tuple[int, int, int], list[int]] = {}
        for i, word in enumerate(data["text"]):
            if str(word).strip() and float(data["conf"][i]) >= 0:
                key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
                groups.setdefault(key, []).append(i)
        out: list[OcrLine] = []
        for idx in groups.values():
            text = " ".join(str(data["text"][i]) for i in idx)
            conf = sum(float(data["conf"][i]) for i in idx) / len(idx) / 100.0
            x0 = min(data["left"][i] for i in idx) * scale
            y0 = min(data["top"][i] for i in idx) * scale
            x1 = max(data["left"][i] + data["width"][i] for i in idx) * scale
            y1 = max(data["top"][i] + data["height"][i] for i in idx) * scale
            out.append(OcrLine(text, round(conf, 4), (round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2))))
        return out
