import json
from pathlib import Path

import miniaudio
import pytest
from mutagen.id3 import ID3
from typer.testing import CliRunner

from sloka_split.cli import app
from sloka_split.mp3frames import parse, parse_header
from sloka_split.splitter import UnsafeOutputError, split_path
from tests.synth import chant, to_mp3

runner = CliRunner()


@pytest.fixture(scope="session")
def mp3_src(tmp_path_factory: pytest.TempPathFactory) -> Path:
    folder = tmp_path_factory.mktemp("src")
    path = folder / "Ch 9 Test.mp3"
    path.write_bytes(to_mp3(chant(sr=44100)))
    return path


def _names(out: Path) -> list[str]:
    return sorted(p.name for p in out.iterdir())


def test_cli_version() -> None:
    r = runner.invoke(app, ["--version"])
    assert r.exit_code == 0 and r.stdout.strip() == "0.1.0"


def test_parse_header_mpeg1_layer3() -> None:
    h = parse_header(bytes([0xFF, 0xFB, 0xB0, 0x40]))  # 192 kbps, 44.1 kHz, stereo
    assert h is not None and h.size == 626 and h.samples == 1152 and h.sample_rate == 44100
    assert parse_header(b"ID3\x03") is None


def test_AC_AS_05_lossless_cut_without_info_frame(mp3_src: Path, tmp_path: Path) -> None:
    data = mp3_src.read_bytes()
    src = parse(data)
    head = data[: src.offsets[0]]
    assert b"Info" in head or b"Xing" in head, "source should start with a LAME Info frame (skipped by parse)"
    [res] = split_path(mp3_src, tmp_path)
    assert "coverage_failed" not in res.warnings
    files = [tmp_path / f"{p.name}.mp3" for p in res.parts]
    assert b"".join(parse(f.read_bytes()).audio_bytes() for f in files) == src.audio_bytes()
    for f in files:
        b = f.read_bytes()
        first = parse(b).offsets[0]
        assert b[first + 4 : first + 60].find(b"Info") < 0 and b[first + 4 : first + 60].find(b"Xing") < 0
        assert miniaudio.decode(b).num_frames > 0


def test_AC_AS_06_names_and_tags(mp3_src: Path, tmp_path: Path) -> None:
    split_path(mp3_src, tmp_path)
    mp3s = [n for n in _names(tmp_path) if n.endswith(".mp3")]
    assert mp3s == ["Ch_9_Test_closing.mp3", "Ch_9_Test_intro.mp3"] + [
        f"Ch_9_Test_sloka_{i:02d}.mp3" for i in range(1, 6)
    ]
    tags = ID3(tmp_path / "Ch_9_Test_sloka_02.mp3")
    assert str(tags["TIT2"]) == "Sloka 2" and str(tags["TRCK"]) == "2/5" and str(tags["TALB"]) == "Ch 9 Test.mp3"
    assert str(ID3(tmp_path / "Ch_9_Test_intro.mp3")["TIT2"]) == "Intro"


def test_AC_AS_07_reports_and_determinism(mp3_src: Path, tmp_path: Path) -> None:
    a, b = tmp_path / "a", tmp_path / "b"
    split_path(mp3_src, a)
    split_path(mp3_src, b)
    report = json.loads((a / "Ch_9_Test.splits.json").read_text())
    assert report["slokas"] == 5 and [p["kind"] for p in report["parts"]] == ["intro", *["sloka"] * 5, "closing"]
    lines = (a / "Ch_9_Test.labels.txt").read_text().splitlines()
    assert len(lines) == 7 and all(len(line.split("\t")) == 3 for line in lines)
    assert _names(a) == _names(b)
    for name in _names(a):
        assert (a / name).read_bytes() == (b / name).read_bytes(), name


def test_AC_AS_08_expected_count_mismatch(mp3_src: Path, tmp_path: Path) -> None:
    r = runner.invoke(app, [str(mp3_src), "-o", str(tmp_path), "--expected", "6"])
    assert r.exit_code == 1 and "count_mismatch" in r.stdout
    assert (tmp_path / "Ch_9_Test_sloka_05.mp3").exists()
    ok = runner.invoke(app, [str(mp3_src), "-o", str(tmp_path / "ok"), "--expected", "5"])
    assert ok.exit_code == 0, ok.stdout


def test_AC_AS_09_clean(mp3_src: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    (out / "sub").mkdir(parents=True)
    (out / "stale.mp3").write_bytes(b"x")
    (out / "sub" / "old.txt").write_text("x")
    r = runner.invoke(app, [str(mp3_src), "-o", str(out), "--clean"])
    assert r.exit_code == 0, r.stdout
    assert "stale.mp3" not in _names(out) and "sub" not in _names(out)

    r = runner.invoke(app, [str(mp3_src), "-o", str(mp3_src.parent), "--clean"])
    assert r.exit_code == 2 and mp3_src.exists()
    with pytest.raises(UnsafeOutputError):
        split_path(mp3_src, mp3_src.parent.parent, clean=True)
    assert mp3_src.exists()


def test_AC_AS_14_review_page(mp3_src: Path, tmp_path: Path) -> None:
    text_file = tmp_path / "t.romanized.jsonl"
    rows = [
        {
            "extracted": {"unit_type": "speaker", "lines": ["सञ्जय उवाच -"], "verse_ref": None},
            "romanized_lines": {"iast": ["sañjaya uvāca -"]},
        },
        {
            "extracted": {
                "unit_type": "verse",
                "lines": ["दृष्ट्वा तु ।", "राजा ॥ २ ॥"],
                "verse_ref": {"label": "॥ २ ॥", "normalized": "2"},
            },
            "romanized_lines": {"iast": ["dṛṣṭvā tu |", "rājā || 2 ||"]},
        },
    ]
    text_file.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    out = tmp_path / "with"
    [res] = split_path(mp3_src, out, text_path=text_file)
    html = (out / "Ch_9_Test.review.html").read_text(encoding="utf-8")
    for p in res.parts:
        assert f'"{p.name}.mp3"' in html
    assert "http://" not in html and "https://" not in html
    data = json.loads(html.split("const DATA = ", 1)[1].split(";\n", 1)[0])
    sloka2 = next(p for p in data["parts"] if p["kind"] == "sloka" and p["number"] == 2)
    assert sloka2["text"] == {
        "speaker": ["sañjaya uvāca -"],
        "dev": rows[1]["extracted"]["lines"],
        "iast": ["dṛṣṭvā tu |", "rājā || 2 ||"],
    }
    assert next(p for p in data["parts"] if p["number"] == 1 and p["kind"] == "sloka")["text"] is None

    plain = tmp_path / "plain"
    split_path(mp3_src, plain)
    data = json.loads((plain / "Ch_9_Test.review.html").read_text().split("const DATA = ", 1)[1].split(";\n", 1)[0])
    assert all(p["text"] is None for p in data["parts"])

    bad = tmp_path / "bad"
    [r] = split_path(mp3_src, bad, text_path=tmp_path / "missing.jsonl")
    assert "text_unreadable" in r.warnings


def test_AC_AS_15_name_option(mp3_src: Path, tmp_path: Path) -> None:
    out = tmp_path / "named"
    r = runner.invoke(app, [str(mp3_src), "-o", str(out), "--name", "CH9"])
    assert r.exit_code == 0, r.stdout
    assert _names(out) == [
        "CH9.labels.txt",
        "CH9.review.html",
        "CH9.splits.json",
        "CH9_closing.mp3",
        "CH9_intro.mp3",
    ] + [f"CH9_sloka_{i:02d}.mp3" for i in range(1, 6)]
    assert str(ID3(out / "CH9_sloka_02.mp3")["TALB"]) == "Ch 9 Test.mp3"

    two = tmp_path / "two"
    two.mkdir()
    for n in ("a.mp3", "b.mp3"):
        (two / n).write_bytes(mp3_src.read_bytes())
    for args in ([str(two), "--name", "CH9"], [str(mp3_src), "--name", "../x"], [str(mp3_src), "--name", ".hidden"]):
        bad = tmp_path / "bad"
        r = runner.invoke(app, [*args, "-o", str(bad)])
        assert r.exit_code == 2, args
        assert not bad.exists() or not any(bad.iterdir())
