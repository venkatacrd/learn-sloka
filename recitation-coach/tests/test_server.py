"""Practice page server: endpoints, local-only, no external URLs (AC-RC-10). Uses a fake recognizer."""

from __future__ import annotations

import io
import json
import re
import threading
import urllib.error
import urllib.request
import wave
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest

from recite_coach.coach import Coach
from recite_coach.library import load_book
from recite_coach.server import page, serve
from tests.conftest import heard

SAID = "धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः मामकाः पाण्दवाश्चैव"  # sloka 1 of the test book, ड said as द


class FakeRecognizer:
    def transcribe(self, pcm: object) -> list:  # type: ignore[type-arg]
        return heard(SAID)


def wav_bytes(seconds: float = 1.0) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        t = np.arange(int(16000 * seconds)) / 16000
        w.writeframes((np.sin(2 * np.pi * 220 * t) * 8000).astype("<i2").tobytes())
    return buf.getvalue()


@pytest.fixture
def url(book: Path, tmp_path: Path) -> Iterator[str]:
    root = tmp_path / "mp3"
    for folder, count in (("1_Ch 01 Complete", 3), ("1_Ch 02 Complete", 1)):
        (root / folder).mkdir(parents=True)
        for k in range(1, count + 1):
            (root / folder / f"x_sloka_{k:02d}.mp3").write_bytes(f"ID3fake-mp3-bytes-ch{folder[5:7]}".encode())
    coach = Coach(load_book(book, root), FakeRecognizer())  # type: ignore[arg-type]
    httpd = serve(coach, 0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def get(u: str, headers: dict[str, str] | None = None) -> tuple[int, bytes, dict[str, str]]:
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers=headers or {})) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)


def test_AC_RC_10_page_has_no_external_urls() -> None:
    html = page().decode("utf-8")
    assert not re.search(r"https?://(?!127\.0\.0\.1)", html)
    assert "<script src" not in html and "@import" not in html


def test_AC_RC_14_endpoints(url: str) -> None:
    code, body, _ = get(url + "/")
    assert code == 200 and b"Sloka recitation practice" in body
    chapters = json.loads(get(url + "/api/chapters")[1])
    assert [(c["number"], c["title_dev"], c["audio_parts"], c["audio_matches"]) for c in chapters] == [
        (1, "अर्जुनविषादयोगः", 3, True), (2, "साङ्ख्ययोगः", 1, False)]  # fmt: skip
    assert chapters[1]["slokas"] == [{"number": 1, "available": True}, {"number": 2, "available": False}]
    s = json.loads(get(url + "/api/sloka/1/1")[1])
    assert s["lines"][0] == {
        "speaker": True,
        "dev": "धृतराष्ट्र उवाच",
        "telugu": "ధృతరాష్ట్ర ఉవాచ",
        "iast": "dhṛtarāṣṭra uvāca",
    }
    assert s["audio_warning"] == "" and "2 slokas" in json.loads(get(url + "/api/sloka/2/1")[1])["audio_warning"]
    assert get(url + "/api/sloka/1/99")[0] == 404 and get(url + "/api/sloka/7/1")[0] == 404
    code, body, hdr = get(url + "/audio/2/1", {"Range": "bytes=3-6"})
    assert code == 206 and body == b"fake" and hdr["Content-Range"].endswith("/22")
    assert get(url + "/audio/2/1")[1].endswith(b"ch02")


def test_check_upload(url: str) -> None:
    req = urllib.request.Request(
        url + "/api/check/2/1", data=wav_bytes(), method="POST", headers={"Content-Type": "audio/wav"}
    )
    with urllib.request.urlopen(req) as r:
        out = json.loads(r.read())
    [f] = out["findings"]
    assert f["kind"] == "retroflex/dental" and f["pada"] == 4 and out["duration_s"] == 1.0
    assert out["chapter"] == 2 and out["sloka"] == 1
    bad = urllib.request.Request(url + "/api/check/2/1", data=b"not audio", method="POST")
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(bad)
    assert e.value.code == 400


def test_foreign_host_refused(url: str) -> None:
    assert get(url + "/api/chapters", {"Host": "evil.example:80"})[0] == 403


def test_AC_RC_15_three_scripts(url: str) -> None:
    s = json.loads(get(url + "/api/sloka/1/1")[1])
    for ln in s["lines"]:
        assert len(ln["dev"].split()) == len(ln["telugu"].split()) == len(ln["iast"].split())
    assert s["lines"][0]["telugu"] == "ధృతరాష్ట్ర ఉవాచ"
    assert s["lines"][1]["telugu"] == "ధర్మక్షేత్రే కురుక్షేత్రే"
    html = page().decode("utf-8")
    for script in ("dev", "tel", "iast"):
        assert re.search(rf'<input type="checkbox" id="show-{script}"[^>]* checked', html), script
