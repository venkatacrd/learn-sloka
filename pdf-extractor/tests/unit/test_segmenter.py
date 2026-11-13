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


def _book_page(number: int, x0: float, x1: float, title: tuple[float, float] | None, verses: int = 12) -> PageResult:
    """A 396-wide book page: optional chapter title, then speaker + numbered verses filling the text frame."""
    rows: list[tuple[str, tuple[float, float]]] = []
    if title:
        rows.append(("साङ्ख्ययोगः", title))
        rows.append(("सञ्जय उवाच -", (x0, x0 + 80)))
    for v in range(1, verses + 1):
        rows.append(("तं तथा कृपयाविष्टम् अश्रुपूर्णाकुलेक्षणम् ।", (x0, x1)))
        rows.append((f"विषीदन्तमिदं वाक्यम् उवाच मधुसूदनः ॥ {v} ॥", (x0, x1 - 10)))
    lines = [
        Line(number, t, normalize(t), (a, 100 + i * 20, b, 114 + i * 20), 16.0, "text_layer", "t", "1")
        for i, (t, (a, b)) in enumerate(rows)
    ]
    return PageResult(number, 396.0, 612.0, PageClass.TEXT_LAYER_OK, lines)


def test_AC_EX_28_title_centred_in_mirrored_text_frame() -> None:
    pages = [
        _book_page(1, 68, 380, (188, 264)),  # odd page: frame centre 224, page centre 198
        _book_page(2, 18, 330, (140, 210)),  # even page: frame centre 174
        _book_page(3, 68, 380, None),
        _book_page(4, 18, 330, None),
    ]
    units = Segmenter(Profile()).segment(pages)
    starts = [i for i, u in enumerate(units) if u.unit_type == "heading"]
    assert len(starts) == 2
    for i in starts:
        assert [u.unit_type for u in units[i : i + 3]] == ["heading", "speaker", "verse"]
        assert units[i + 2].verse_ref == {"label": "॥ 1 ॥", "normalized": "1"}
        assert all("साङ्ख्ययोगः" not in ln.text for ln in units[i + 2].lines)

    few = Segmenter(Profile()).segment([_book_page(1, 68, 380, (188, 264), verses=3)])  # < 20 wide lines
    assert few[0].unit_type != "heading"  # page centre used: the off-centre title is not a heading


def test_AC_EX_29_speaker_with_joined_uvaca() -> None:
    for speaker in ("श्री भगवानुवाच -", "श्रीभगवानुवाच", "अर्जुन उवाच -"):
        units = Segmenter(Profile()).segment(
            [_page([speaker, "कुतस्त्वा कश्मलमिदं विषमे समुपस्थितम् ।", "अनार्यजुष्टमस्वर्ग्यम् अकीर्तिकरमर्जुन ॥ २ ॥"])]
        )
        assert [u.unit_type for u in units] == ["speaker", "verse"], speaker
        assert len(units[1].lines) == 2
