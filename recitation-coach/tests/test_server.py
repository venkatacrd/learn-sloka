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
from recite_coach.library import load_chapter
from recite_coach.server import page, serve
from tests.conftest import heard

SAID = "धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः मामकाः पाण्दवाश्चैव किमकुर्वत सञ्जय"


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
def url(chapter: Path, tmp_path: Path) -> Iterator[str]:
    audio = tmp_path / "audio"
    audio.mkdir()
    (audio / "x_sloka_01.mp3").write_bytes(b"ID3fake-mp3-bytes-0123456789")
    coach = Coach(load_chapter(chapter, audio), FakeRecognizer())  # type: ignore[arg-type]
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


def test_endpoints(url: str) -> None:
    code, body, _ = get(url + "/")
    assert code == 200 and b"Sloka recitation practice" in body
    slokas = json.loads(get(url + "/api/slokas")[1])
    assert {"number": 1, "available": True} in slokas and {"number": 21, "available": False} in slokas
    s = json.loads(get(url + "/api/sloka/1")[1])
    assert s["lines"][0] == {"speaker": True, "dev": "धृतराष्ट्र उवाच", "iast": "dhṛtarāṣṭra uvāca"}
    assert get(url + "/api/sloka/99")[0] == 404
    code, body, hdr = get(url + "/audio/1", {"Range": "bytes=3-6"})
    assert code == 206 and body == b"fake" and hdr["Content-Range"].endswith("/28")


def test_check_upload(url: str) -> None:
    req = urllib.request.Request(
        url + "/api/check/1", data=wav_bytes(), method="POST", headers={"Content-Type": "audio/wav"}
    )
    with urllib.request.urlopen(req) as r:
        out = json.loads(r.read())
    [f] = out["findings"]
    assert f["kind"] == "retroflex/dental" and f["pada"] == 3 and out["duration_s"] == 1.0
    bad = urllib.request.Request(url + "/api/check/1", data=b"not audio", method="POST")
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(bad)
    assert e.value.code == 400


def test_foreign_host_refused(url: str) -> None:
    assert get(url + "/api/slokas", {"Host": "evil.example:80"})[0] == 403
