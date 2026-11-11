"""EX-T14: NFR-EX-03 (≥ 20 pages/s on the text-layer path). Run with `pytest -m slow`."""

import time
from pathlib import Path

import pymupdf
import pytest

from sanskrit_extract.config import Config
from sanskrit_extract.pipeline import extract
from tests.conftest import REFERENCE_PDF


@pytest.mark.slow
def test_NFR_EX_03_text_layer_speed(tmp_path: Path) -> None:
    if not REFERENCE_PDF.exists():
        pytest.skip("reference PDF missing")
    src = pymupdf.open(REFERENCE_PDF)
    big = pymupdf.open()
    for _ in range(50):  # 200 pages
        big.insert_pdf(src)
    path = tmp_path / "big.pdf"
    big.save(path)
    start = time.perf_counter()
    units = extract(path, Config(), lambda: (_ for _ in ()).throw(AssertionError("no OCR")))
    rate = 200 / (time.perf_counter() - start)
    assert len([u for u in units.units if u["unit_type"] == "verse"]) == 47 * 50
    assert rate >= 20, f"{rate:.1f} pages/s"
