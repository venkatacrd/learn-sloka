from pathlib import Path

from sanskrit_extract.pdf_reader import PdfDocument
from tests.fixtures.factory import T, make_pdf


def test_fixture_roundtrip_text(tmp_path: Path) -> None:
    s = "धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः ।"
    pdf = make_pdf(tmp_path / "a.pdf", [[T(s, 100)]])
    with PdfDocument(pdf) as doc:
        assert doc.page(1).lines[0].text == s
