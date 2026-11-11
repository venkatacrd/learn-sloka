"""Contract schemas (NFR-TR-01, 05). Bundled into the package from specs/contracts at build time."""

from __future__ import annotations

import json
from functools import cache
from importlib.resources import files
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource


def contract_text(name: str) -> str:
    """Bundled copy when installed; the repository's specs/contracts when run from source."""
    bundled = files("sanskrit_romanize") / "contracts" / name
    if bundled.is_file():
        return bundled.read_text(encoding="utf-8")
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "specs" / "contracts" / name
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
    raise FileNotFoundError(f"contract {name} not found (bundled or in specs/contracts)")


def _load(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(contract_text(name))
    return data


@cache
def validators() -> tuple[Draft202012Validator, Draft202012Validator]:
    extracted = _load("extracted-unit.schema.json")
    romanized = _load("romanized-unit.schema.json")
    res = Resource.from_contents(extracted)
    registry: Registry = Registry().with_resources(
        [
            (extracted["$id"], res),
            ("extracted-unit.schema.json", res),
            ("romanized-unit/extracted-unit.schema.json", res),
        ]
    )
    return Draft202012Validator(extracted, registry=registry), Draft202012Validator(romanized, registry=registry)


def errors(validator: Draft202012Validator, obj: Any) -> list[str]:
    return [f"{list(e.path)}: {e.message}" for e in sorted(validator.iter_errors(obj), key=lambda e: list(e.path))]
