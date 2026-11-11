from pathlib import Path

from sanskrit_romanize.contracts import contract_text, errors, validators
from tests.conftest import unit


def test_schemas_load_and_sample_is_valid() -> None:
    in_v, out_v = validators()
    assert in_v.schema["$id"] == "extracted-unit/1.2.0"
    assert out_v.schema["$id"] == "romanized-unit/1.0.0"
    assert errors(in_v, unit()) == []
    assert errors(in_v, unit(unit_type="poem"))


def test_loaded_contracts_match_specs() -> None:
    specs = Path(__file__).resolve().parents[3] / "specs" / "contracts"
    for name in ("extracted-unit.schema.json", "romanized-unit.schema.json"):
        assert contract_text(name) == (specs / name).read_text(encoding="utf-8"), f"{name} is stale: run `uv sync`"


def test_NFR_TR_05_no_import_of_extractor() -> None:
    src = Path(__file__).resolve().parents[2] / "src"
    assert not [p for p in src.rglob("*.py") if "sanskrit_extract" in p.read_text(encoding="utf-8")]
