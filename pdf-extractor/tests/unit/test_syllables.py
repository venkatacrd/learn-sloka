import pytest

from sanskrit_extract.syllables import deva_ratio, script_of, syllable_validity


@pytest.mark.parametrize(
    "text",
    ["धर्मक्षेत्रे", "कुरुक्षेत्रे", "पश्यैतां", "वीर्यवान्", "मेऽच्युत", "ॐ", "॥ १ ॥", "संज्ञार्थं", "अग्निमी॑ळे", "कृत्स्नम्"],
)
def test_valid_clusters(text: str) -> None:
    assert syllable_validity(text) == 1.0


@pytest.mark.parametrize("text", ["िक", "ाम", "क्ािम", "्क"])
def test_invalid_clusters(text: str) -> None:
    assert syllable_validity(text) < 1.0


def test_ratios_and_script() -> None:
    assert deva_ratio("abc") == 0.0
    assert deva_ratio("धर्म abc") == pytest.approx(3 / 6)
    assert deva_ratio("123 ।") == 1.0
    assert script_of("धर्म") == "devanagari"
    assert script_of("dharma") == "latin"
    assert script_of("धर्म dharma") == "mixed"
    assert script_of("12") == "unknown"
