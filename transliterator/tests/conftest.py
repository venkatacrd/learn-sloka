from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REFERENCE_PDF = ROOT / "01_Chapter_Sanskrit.pdf"
EXTRACTOR = ROOT / "pdf-extractor"

_BASE: dict[str, Any] = {
    "schema_version": "1.2.0",
    "doc_id": "gita-1a2b3c4d",
    "unit_id": "gita-1a2b3c4d:000001",
    "seq": 1,
    "unit_type": "verse",
    "verse_ref": {"label": "॥ १ ॥", "normalized": "1"},
    "source": {"file_name": "gita.pdf", "sha256": "0" * 64, "page_start": 1, "page_end": 1},
    "text_raw": "raw",
    "text": "धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः । मामकाः पाण्डवाश्चैव किमकुर्वत सञ्जय ॥ १ ॥",
    "lines": ["धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः ।", "मामकाः पाण्डवाश्चैव किमकुर्वत सञ्जय ॥ १ ॥"],
    "script": "devanagari",
    "extraction": {"method": "text_layer", "tool": "pymupdf", "tool_version": "1"},
    "quality": {"score": 1.0, "ocr_confidence": None, "flags": []},
}


def unit(**patch: Any) -> dict[str, Any]:
    """A hand-written extracted-unit (002 depends on the contract only, NFR-TR-05)."""
    u = copy.deepcopy(_BASE)
    for k, v in patch.items():
        u[k] = v
    if "text" in patch and "lines" not in patch:
        u["lines"] = [patch["text"]]
    return u


def write_jsonl(path: Path, units: list[dict[str, Any]], extra_lines: list[str] | None = None) -> Path:
    rows = [json.dumps(u, ensure_ascii=False) for u in units] + (extra_lines or [])
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path
