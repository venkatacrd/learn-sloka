import pytest
from hypothesis import given
from hypothesis import strategies as st

from sanskrit_romanize.api import romanize
from sanskrit_romanize.config import Config
from sanskrit_romanize.engines.sanscript_engine import SanscriptEngine
from sanskrit_romanize.roundtrip import check

ENGINE = SanscriptEngine()


def test_AC_TR_01_gita_line() -> None:
    assert romanize("धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः ।") == "dharmakṣetre kurukṣetre samavetā yuyutsavaḥ |"


def test_AC_TR_02_ascii_fold() -> None:
    assert romanize("धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः ।", "ascii") == "dharmaksetre kuruksetre samaveta yuyutsavah"


@pytest.mark.parametrize(
    ("scheme", "expected"),
    [("iast", "kṛṣṇaḥ"), ("iso15919", "kr̥ṣṇaḥ"), ("hk", "kRSNaH"), ("slp1", "kfzRaH")],
)
def test_AC_TR_03_schemes(scheme: str, expected: str) -> None:
    assert romanize("कृष्णः", scheme) == expected


@pytest.mark.parametrize(
    ("dev", "iast"),
    [
        ("सोऽहम्", "so'ham"),
        ("ॐ", "oṃ"),
        ("संस्कृतम्", "saṃskṛtam"),
        ("हँस", "ham̐sa"),
        ("॥ ४७ ॥", "|| 47 ||"),
        ("ज्ञानम्", "jñānam"),
        ("ऋतम्", "ṛtam"),
        ("पितॄन्", "pitṝn"),
        ("कॢप्त", "kḷpta"),
    ],
)
def test_AC_TR_04_sanskrit_specifics(dev: str, iast: str) -> None:
    assert romanize(dev) == iast
    assert check(dev, iast, ENGINE, Config()) is None


@pytest.mark.parametrize(("dev", "iast"), [("कइ", "kaï"), ("प्रउग", "praüga"), ("अइ", "aï"), ("कै", "kai")])
def test_AC_TR_14_hiatus_is_unambiguous(dev: str, iast: str) -> None:
    assert romanize(dev) == iast
    assert check(dev, iast, ENGINE, Config()) is None


def test_danda_and_digit_styles() -> None:
    cfg = Config(danda_style="devanagari", digits="devanagari")
    out = romanize("सञ्जय ॥ १ ॥", config=cfg)
    assert out == "sañjaya ॥ १ ॥"
    assert check("सञ्जय ॥ १ ॥", out, ENGINE, cfg) is None
    assert romanize("सञ्जय । ॥", config=Config(danda_style="period")) == "sañjaya . .."


_C = list("कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसह")
_V = [*"ािीुूृॄेैोौ", ""]
syllable = st.builds(lambda c, v: c + v, st.sampled_from(_C), st.sampled_from(_V))
word = st.lists(st.one_of(syllable, st.sampled_from(["अ", "आ", "इ", "उ", "ए", "ओ"])), min_size=1, max_size=6).map(
    "".join
)


@given(st.lists(word, min_size=1, max_size=5).map(" ".join))
def test_property_iast_round_trips(text: str) -> None:
    assert check(text, romanize(text), ENGINE, Config()) is None
