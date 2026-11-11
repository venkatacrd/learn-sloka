"""Image preprocessing before OCR: grayscale, binarize (Otsu), deskew. Needs the `ocr` extra."""

from __future__ import annotations

from typing import Any


def preprocess(png: bytes) -> Any:
    import cv2
    import numpy as np

    img = cv2.imdecode(np.frombuffer(png, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("could not decode the rendered page image")
    _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    coords = np.column_stack(np.where(binary < 128))
    if len(coords) > 100:
        angle = cv2.minAreaRect(coords.astype(np.float32))[-1]
        angle = angle - 90 if angle > 45 else angle
        if 0.1 < abs(angle) < 10:
            h, w = binary.shape
            m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
            binary = cv2.warpAffine(binary, m, (w, h), flags=cv2.INTER_CUBIC, borderValue=255)
    return binary
