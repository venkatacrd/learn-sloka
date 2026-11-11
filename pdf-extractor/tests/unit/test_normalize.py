import unicodedata

import pytest
from hypothesis import given
from hypothesis import strategies as st

from sanskrit_extract.normalize import (
    NormalizeConfig,
    collapse_spaces,
    danda_lookalikes,
    danda_spacing,
    normalize,
    remove_soft_hyphen_and_controls,
    zero_width_joiners,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("सञ्जय॥ १॥", "सञ्जय ॥ १ ॥"),
        ("सखींस्तथा॥२६॥", "सखींस्तथा ॥ २६ ॥"),
        ("युयुत्सवः।", "युयुत्सवः ।"),
        ("॥ ॐ श्री परमात्मने नमः॥", "॥ ॐ श्री परमात्मने नमः ॥"),
        ("सञ्जय ॥ २-४७ ॥", "सञ्जय ॥ २-४७ ॥"),
    ],
)
def test_danda_spacing(raw: str, expected: str) -> None:
    assert danda_spacing(raw) == expected


def test_danda_lookalikes_only_next_to_devanagari() -> None:
    assert danda_lookalikes("युयुत्सवः |") == "युयुत्सवः ।"
    assert danda_lookalikes("सञ्जय || १ ||") == "सञ्जय ॥ १ ॥"
    assert danda_lookalikes("a | b || I") == "a | b || I"


def test_controls_soft_hyphen_and_spaces() -> None:
    assert remove_soft_hyphen_and_controls("धर्­म\x07") == "धर्म"
    assert collapse_spaces("धर्म     क्षेत्रे ") == "धर्म क्षेत्रे"


def test_zwj_kept_only_after_virama() -> None:
    assert zero_width_joiners("क्‍ष") == "क्‍ष"
    assert zero_width_joiners("क‍ष") == "कष"


def test_each_rule_can_be_switched_off() -> None:
    assert normalize("सञ्जय॥ १॥", NormalizeConfig(danda_spacing=False)) == "सञ्जय॥ १॥"


def test_nfc() -> None:
    decomposed = unicodedata.normalize("NFD", "क़")
    assert normalize(decomposed) == unicodedata.normalize("NFC", "क़")


deva = st.text(alphabet=st.characters(min_codepoint=0x0900, max_codepoint=0x097F) | st.sampled_from(" |­‌"))


@given(deva)
def test_normalize_is_idempotent_and_nfc(s: str) -> None:
    once = normalize(s)
    assert normalize(once) == once
    assert unicodedata.is_normalized("NFC", once)
