"""Deterministic JSONL + report output (FR-EX-14, NFR-EX-02)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write_outputs(outdir: Path, doc_id: str, units: list[dict[str, Any]], report: dict[str, Any]) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    jsonl = "".join(dumps(u) + "\n" for u in units)
    (outdir / f"{doc_id}.jsonl").write_text(jsonl, encoding="utf-8", newline="\n")
    (outdir / f"{doc_id}.report.json").write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
