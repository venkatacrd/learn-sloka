"""RAG-ready view of a unit (FR-TR-09)."""

from __future__ import annotations

from typing import Any


def pages_label(source: dict[str, Any]) -> str:
    a, b = source["page_start"], source["page_end"]
    return str(a) if a == b else f"{a}-{b}"


def citation(ex: dict[str, Any]) -> str:
    out = f"{ex['source']['file_name']} p.{pages_label(ex['source'])}"
    if ex.get("verse_ref"):
        out += f", verse {ex['verse_ref']['normalized']}"
    return out


def build(ex: dict[str, Any], romanized: dict[str, str], embedding_text: str) -> dict[str, Any]:
    iast, dev = romanized["iast"], ex["text"]
    keyword = [romanized["ascii"]] if "ascii" in romanized else []
    return {
        "id": ex["unit_id"],
        "text_for_embedding": iast if embedding_text == "iast" else dev,
        "text_for_keyword": " ".join([*keyword, iast, dev]),
        "display_text": f"{dev}\n{iast}",
        "citation": citation(ex),
        "metadata": {
            "doc_id": ex["doc_id"],
            "unit_type": ex["unit_type"],
            "verse_ref": (ex.get("verse_ref") or {}).get("normalized"),
            "pages": pages_label(ex["source"]),
            "quality_score": ex["quality"]["score"],
            "flags": ex["quality"]["flags"],
        },
    }
