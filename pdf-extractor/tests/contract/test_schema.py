import copy
from typing import Any

import pytest

from tests.conftest import VALIDATOR, assert_valid_unit

SAMPLE: dict[str, Any] = {
    "schema_version": "1.2.0",
    "doc_id": "gita-1a2b3c4d",
    "unit_id": "gita-1a2b3c4d:000001",
    "seq": 1,
    "unit_type": "verse",
    "verse_ref": {"label": "॥ १ ॥", "normalized": "1"},
    "source": {"file_name": "gita.pdf", "sha256": "0" * 64, "page_start": 1, "page_end": 1},
    "text_raw": "raw",
    "text": "धर्मक्षेत्रे",
    "lines": ["धर्मक्षेत्रे"],
    "script": "devanagari",
    "extraction": {"method": "legacy_font_map", "tool": "sanskrit99", "tool_version": "0.1.0"},
    "quality": {"score": 1.0, "ocr_confidence": None, "flags": []},
}


def test_schema_loads() -> None:
    assert VALIDATOR.schema["$id"] == "extracted-unit/1.2.0"


def test_valid_sample_accepted() -> None:
    assert_valid_unit(SAMPLE)


def test_speaker_unit_type_accepted() -> None:
    unit = copy.deepcopy(SAMPLE) | {"unit_type": "speaker", "verse_ref": None}
    assert_valid_unit(unit)


@pytest.mark.parametrize(
    "patch",
    [{"unit_type": "poem"}, {"schema_version": "1.0.0"}, {"extra": 1}, {"seq": -1}],
)
def test_invalid_sample_rejected(patch: dict[str, Any]) -> None:
    unit = copy.deepcopy(SAMPLE) | patch
    with pytest.raises(AssertionError):
        assert_valid_unit(unit)
