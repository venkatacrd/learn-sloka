from sanskrit_extract.config import Profile
from sanskrit_extract.models import Line, PageClass, PageResult
from sanskrit_extract.normalize import normalize
from sanskrit_extract.segmenter import Segmenter, normalize_ref


def _page(texts: list[str], number: int = 1, step: float = 20.0) -> PageResult:
    lines = [
        Line(number, t, normalize(t), (60.0, 100 + i * step, 400.0, 114 + i * step), 14.0, "text_layer", "t", "1")
        for i, t in enumerate(texts)
    ]
    return PageResult(number, 595.0, 842.0, PageClass.TEXT_LAYER_OK, lines)


def test_AC_EX_06_one_verse_with_ref_and_two_lines() -> None:
    units = Segmenter(Profile()).segment(
        [_page(["धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः ।", "मामकाः पाण्डवाश्चैव किमकुर्वत सञ्जय ॥ १-१ ॥"])]
    )
    assert [u.unit_type for u in units] == ["verse"]
    assert units[0].verse_ref == {"label": "॥ १-१ ॥", "normalized": "1.1"}
    assert len(units[0].lines) == 2


def test_verse_ref_formats() -> None:
    assert normalize_ref("॥ १ ॥") == "1"
    assert normalize_ref("॥ २-४७ ॥") == "2.47"
    assert normalize_ref("॥ २.४७ ॥") == "2.47"
    assert normalize_ref("1.47") == "1.47"


def test_ascii_verse_number_closes_verse() -> None:
    units = Segmenter(Profile()).segment([_page(["धर्मक्षेत्रे कुरुक्षेत्रे ।", "मामकाः पाण्डवाश्चैव 1.47"])])
    assert units[0].unit_type == "verse"
    assert units[0].verse_ref == {"label": "1.47", "normalized": "1.47"}


def test_unnumbered_verse_flagged() -> None:
    units = Segmenter(Profile()).segment([_page(["धर्मक्षेत्रे ।", "मामकाः पाण्डवाश्चैव ॥"])])
    assert units[0].unit_type == "verse"
    assert units[0].verse_ref is None
    assert "unnumbered_verse" in units[0].flags


def test_unfinished_text_becomes_other_needing_review() -> None:
    units = Segmenter(Profile()).segment([_page(["यह साधारण वाक्य है"])])
    assert units[0].unit_type == "other"
    assert units[0].flags == ["needs_review"]


def test_title_before_a_gap_is_a_heading() -> None:
    page = _page(["पुरुषोत्तमप्राप्तियोगः", "ऊर्ध्वमूलमधःशाखम् अश्वत्थं प्राहुरव्ययम् ।", "छन्दांसि यस्य पर्णानि यस्तं वेद स वेदवित् ॥ १ ॥"])
    first = page.lines[0]
    first.bbox = (60.0, 40.0, 200.0, 54.0)  # big gap before the verse
    units = Segmenter(Profile()).segment([page])
    assert [u.unit_type for u in units] == ["heading", "verse"]


def test_verse_starting_with_iti_or_om_tatsat_is_a_verse() -> None:
    units = Segmenter(Profile()).segment(
        [
            _page(
                [
                    "इति क्षेत्रं तथा ज्ञानं ज्ञेयं चोक्तं समासतः ।",
                    "मद्भक्त एतद्विज्ञाय मद्भावायोपपद्यते ॥ १८ ॥",
                    "ॐ तत्सदिति निर्देशः ब्रह्मणस्त्रिविधः स्मृतः ।",
                    "ब्राह्मणास्तेन वेदाश्च यज्ञाश्च विहिताः पुरा ॥ २३ ॥",
                ]
            )
        ]
    )
    assert [(u.unit_type, (u.verse_ref or {}).get("normalized")) for u in units] == [("verse", "18"), ("verse", "23")]
