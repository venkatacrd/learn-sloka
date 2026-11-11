"""Sanskrit99 mapping (FR-EX-05, Q9). Expected strings checked against the rendered reference PDF."""

import pytest

from sanskrit_extract.legacy_fonts.sanskrit99 import decode

CASES = [
    ("xmR]eÇe k…é]eÇe", "धर्मक्षेत्रे कुरुक्षेत्रे"),  # reph + ligatures
    ("AjuRniv;adyaeg>", "अर्जुनविषादयोगः"),  # reph after matra, prefix i
    ("iSwtaE", "स्थितौ"),  # prefix i before a half consonant
    ("pZyiNt", "पश्यन्ति"),
    ("àpZyiÑjRnadRn", "प्रपश्यद्भिर्जनार्दन"),
    ("s<}aw¡", "संज्ञार्थं"),  # reph + anusvara glyph
    ("ktu¡", "कर्तुं"),
    ("ÊyaeRxn", "दुर्योधन"),
    ("†:qœva", "दृष्ट्वा"),
    ("x&traò+", "धृतराष्ट्र"),
    ("shsEva_yhNyNt", "सहसैवाभ्यहन्यन्त"),
    ("k«Tõm!", "कृत्स्नम्"),
    ("sEaÉÔí", "सौभद्रश्च"),  # ौ keyed in reverse order
    ("Ty®va", "त्यक्त्वा"),
    ("sÃy. 1.", "सञ्जय॥ १॥"),
    ("me=Cyut", "मेऽच्युत"),
    # 1.1.0 codes, raw strings from SrimadBhagawadGeeta_Sanskrit.pdf
    ("buÏ(a", "बुद्ध्या"),
    ("zalbuÏe )…‘arivNda", "शालबुद्धे फुल्लारविन्दा"),
    ("daeGxa", "दोग्धा"),
    ("kLpte", "कल्पते"),
    ("At ^Xv¡", "अत ऊर्ध्वं"),
    ("zuÉa~‘aekan!", "शुभाँल्लोकान्"),
    ("s'œ¢am<", "सङ्ग्रामं"),
    ("blvÎ¯Fm!", "बलवद्दृढम्"),
    ("maehaÌ¯hITva=sÍahan!", "मोहाद्गृहीत्वाऽसद्ग्राहान्"),
    ("naTyuiCÀt<", "नात्युच्छ्रितं"),
    ("}ansiÁDÚs<zym", "ज्ञानसञ्छिन्नसंशयम"),
    ("nEtÅvYyupp*te", "नैतत्त्वय्युपपद्यते"),
    ("raÈyagme", "रात्र्यागमे"),
    ("ïImËijRtm!", "श्रीमदूर्जितम्"),
    ("n cEtiÖÒ>", "न चैतद्विद्मः"),
    ("ik< tÓ+ü", "किं तद्ब्रह्म"),
    ("kmRsÛyasyaeg>", "कर्मसन्न्यासयोगः"),
    ("vsUÜuÔan!", "वसून्रुद्रान्"),
    ("AlaeluÞv<", "अलोलुप्त्वं"),
    ("xUmenaiìyte viû>", "धूमेनाव्रियते वह्निः"),
    ("ytvaŠaymans>", "यतवाक्कायमानसः"),
    ("Éu“e", "भुङ्क्ते"),
    ("AVy´a™´y>", "अव्यक्ताद्व्यक्तयः"),
    ("g&Ÿait", "गृह्णाति"),
    ("à’adíaiSm", "प्रह्लादश्चास्मि"),
    ("ÉgvÔƒp<", "भगवद्रूपं"),
    ("` ïI prmaTmne nm>", "ॐ श्री परमात्मने नमः"),
]


@pytest.mark.parametrize(("raw", "expected"), CASES)
def test_decode(raw: str, expected: str) -> None:
    text, unknown = decode(raw)
    assert text == expected
    assert unknown == []


def test_i_matra_reordering_moves_sign_after_whole_cluster() -> None:
    assert decode("iÖj")[0] == "द्विज"
    assert decode("ASmak<")[0] == "अस्माकं"


def test_unknown_code_is_kept_and_reported_not_guessed() -> None:
    text, unknown = decode("k§")
    assert text == "क§"
    assert unknown == ["§"]
