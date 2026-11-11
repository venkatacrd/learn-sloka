from sloka_split.analysis import HALF_VERSE_END_UNCERTAIN, NO_CADENCE_PATTERN, Settings, analyze, otsu_threshold
from tests.synth import chant


def _check_boundaries(result, c) -> None:  # type: ignore[no-untyped-def]
    slokas = result.slokas
    assert len(slokas) == len(c.sloka_spans)
    for part, (voice_start, voice_end) in zip(slokas, c.sloka_spans, strict=True):
        assert part.start_s < voice_start + 0.02, part
        assert part.end_s > voice_end - 0.02, part
        assert part.cadences == 2


def test_AC_AS_01_slokas_intro_closing_and_speaker() -> None:
    c = chant()
    r = analyze(c.pcm, c.sample_rate)
    assert r.warnings == []
    assert [p.kind for p in r.parts] == ["intro"] + ["sloka"] * 5 + ["closing"]
    _check_boundaries(r, c)
    assert r.slokas[2].segments == 5  # speaker segment belongs to the sloka it introduces
    assert r.parts[0].segments == 2 and r.parts[-1].segments == 2


def test_AC_AS_02_split_pada_does_not_shift_boundaries() -> None:
    plain = analyze(*(lambda c: (c.pcm, c.sample_rate))(chant()))
    c = chant(split_pada=(4, 1))
    r = analyze(c.pcm, c.sample_rate)
    _check_boundaries(r, c)
    assert r.slokas[3].segments == 5
    # boundaries before the split are identical; later ones are shifted only by the extra breath pause
    for a, b in zip(plain.slokas[:3], r.slokas[:3], strict=True):
        assert abs(a.end_s - b.end_s) < 0.02


def test_AC_AS_03_monotone_audio_has_no_cadence_pattern() -> None:
    c = chant(monotone=True)
    r = analyze(c.pcm, c.sample_rate)
    assert NO_CADENCE_PATTERN in r.warnings
    assert r.slokas == []


def test_AC_AS_04_cuts_lie_inside_pauses() -> None:
    c = chant(split_pada=(2, 0))
    r = analyze(c.pcm, c.sample_rate)
    end = len(c.pcm) / c.sample_rate
    for part in r.parts[:-1]:
        assert any(a - 0.01 <= part.end_s <= b + 0.01 for a, b in c.gaps), part.end_s
    assert r.parts[0].start_s == 0.0 and r.parts[-1].end_s == end


def test_odd_cadence_count_warns() -> None:
    c = chant(slokas=3, speaker_before=None, closing=0)
    # chop the last half-verse: drop audio after the 5th cadence
    r = analyze(c.pcm[: int((c.sloka_spans[2][0] + 6.6) * c.sample_rate)], c.sample_rate)
    assert "incomplete_last_sloka" in r.warnings
    assert r.slokas[-1].cadences == 1


def test_otsu_separates_two_groups() -> None:
    thr, sep = otsu_threshold([1.0, 1.2, 0.9, 5.0, 5.1, 4.8])  # type: ignore[misc]
    assert 1.2 < thr < 4.8 and sep > 3.5
    assert otsu_threshold([2.0, 2.0]) is None


def test_AC_AS_11_falling_pitch_on_lines_1_and_3_auto_detected() -> None:
    """Reference-recording style: the half-verse ends on the line *after* the falling pitch."""
    c = chant(style="next", split_pada=(2, 3))
    r = analyze(c.pcm, c.sample_rate)
    assert r.half_verse_end == "next" and r.warnings == []
    assert [p.kind for p in r.parts] == ["intro"] + ["sloka"] * 5 + ["closing"]
    _check_boundaries(r, c)
    assert r.slokas[2].segments == 5 and r.parts[0].segments == 2 and r.parts[-1].segments == 2

    plain = chant(style="cadence")
    assert analyze(plain.pcm, plain.sample_rate).half_verse_end == "cadence"


def test_AC_AS_12_half_verse_end_override() -> None:
    c = chant(style="next")
    forced = analyze(c.pcm, c.sample_rate, Settings(half_verse_end="cadence"))
    assert forced.half_verse_end == "cadence" and forced.half_verse_vote is None
    ok = analyze(c.pcm, c.sample_rate, Settings(half_verse_end="next"))
    assert ok.half_verse_end == "next"
    _check_boundaries(ok, c)
    # the override is honoured: forcing "next" on cadence-style audio moves the cuts
    c2 = chant(style="cadence")
    auto2 = analyze(c2.pcm, c2.sample_rate)
    forced2 = analyze(c2.pcm, c2.sample_rate, Settings(half_verse_end="next"))
    assert [p.end_s for p in forced2.slokas] != [p.end_s for p in auto2.slokas]


def test_AC_AS_13_equal_pauses_make_auto_uncertain() -> None:
    import tests.synth as synth

    old = synth.SHORT, synth.LONG
    synth.SHORT = synth.LONG = 0.5
    try:
        c = chant(style="next")
    finally:
        synth.SHORT, synth.LONG = old
    r = analyze(c.pcm, c.sample_rate)
    assert HALF_VERSE_END_UNCERTAIN in r.warnings
