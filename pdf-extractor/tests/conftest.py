from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "specs" / "contracts"
SAMPLES = ROOT / "samples"
REFERENCE_PDF = ROOT / "01_Chapter_Sanskrit.pdf"
GOLD_DIR = SAMPLES / "gold"


def _validator() -> Draft202012Validator:
    schema = json.loads((CONTRACTS / "extracted-unit.schema.json").read_text(encoding="utf-8"))
    registry: Registry = Registry().with_resource(schema["$id"], Resource.from_contents(schema))
    return Draft202012Validator(schema, registry=registry)


VALIDATOR = _validator()


def assert_valid_unit(unit: dict[str, Any]) -> None:
    errors = sorted(VALIDATOR.iter_errors(unit), key=lambda e: list(e.path))
    assert not errors, "; ".join(f"{list(e.path)}: {e.message}" for e in errors)


@pytest.fixture
def reference_pdf() -> Path:
    if not REFERENCE_PDF.exists():
        pytest.skip("reference PDF missing")
    return REFERENCE_PDF


def gold_pages(stem: str) -> dict[int, str]:
    """Gold text files for a PDF stem, keyed by page number (Q1b)."""
    out: dict[int, str] = {}
    for p in sorted(GOLD_DIR.glob(f"{stem}_p*.txt")):
        out[int(p.stem.rsplit("_p", 1)[1])] = p.read_text(encoding="utf-8")
    return out
