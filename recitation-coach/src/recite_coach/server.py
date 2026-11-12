"""Local practice page server: 127.0.0.1 only, no external resources (FR-RC-03, NFR-RC-01)."""

from __future__ import annotations

import json
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from typing import Any

from .coach import Coach, UnknownSloka
from .model import decode_audio

MAX_UPLOAD = 25 * 1024 * 1024  # ~13 min of 16 kHz WAV
_ALLOWED_HOSTS = {"127.0.0.1", "localhost"}


def page() -> bytes:
    return (files("recite_coach") / "static" / "index.html").read_bytes()


def make_handler(coach: Coach) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "recite-coach"

        def log_message(self, fmt: str, *args: Any) -> None:  # quiet console
            pass

        def _host_ok(self) -> bool:
            host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]")
            if host not in _ALLOWED_HOSTS:  # blocks DNS-rebinding style access
                self.send_error(HTTPStatus.FORBIDDEN)
                return False
            return True

        def _send(self, body: bytes, ctype: str, status: int = 200, extra: dict[str, str] | None = None) -> None:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj: Any, status: int = 200) -> None:
            self._send(json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", status)

        def do_GET(self) -> None:
            if not self._host_ok():
                return
            path = self.path.split("?", 1)[0]
            try:
                if path in ("/", "/index.html"):
                    self._send(page(), "text/html; charset=utf-8")
                elif path == "/api/slokas":
                    self._json([{"number": n, "available": s.available} for n, s in coach.slokas.items()])
                elif m := re.fullmatch(r"/api/sloka/(\d+)", path):
                    self._json(coach.sloka_json(int(m.group(1))))
                elif m := re.fullmatch(r"/audio/(\d+)", path):
                    self._audio(int(m.group(1)))
                else:
                    self.send_error(HTTPStatus.NOT_FOUND)
            except UnknownSloka:
                self._json({"error": "unknown sloka"}, 404)

        def _audio(self, n: int) -> None:
            src = coach.sloka(n).audio
            if src is None:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            data = src.read_bytes()
            rng = re.fullmatch(r"bytes=(\d*)-(\d*)", self.headers.get("Range") or "")
            if rng and (rng.group(1) or rng.group(2)):  # seeking in the instructor audio needs ranges
                a = int(rng.group(1)) if rng.group(1) else len(data) - int(rng.group(2))
                b = int(rng.group(2)) if rng.group(1) and rng.group(2) else len(data) - 1
                b = min(b, len(data) - 1)
                self._send(data[a : b + 1], "audio/mpeg", 206,
                           {"Content-Range": f"bytes {a}-{b}/{len(data)}", "Accept-Ranges": "bytes"})  # fmt: skip
            else:
                self._send(data, "audio/mpeg", 200, {"Accept-Ranges": "bytes"})

        def do_POST(self) -> None:
            if not self._host_ok():
                return
            m = re.fullmatch(r"/api/check/(\d+)", self.path.split("?", 1)[0])
            if not m:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            size = int(self.headers.get("Content-Length") or 0)
            if not 0 < size <= MAX_UPLOAD:
                self._json({"error": "recording missing or too large"}, 413)
                return
            body = self.rfile.read(size)
            try:
                result = coach.check(int(m.group(1)), decode_audio(body))
            except UnknownSloka:
                self._json({"error": "unknown sloka"}, 404)
                return
            except Exception as exc:  # undecodable upload etc.: report, keep serving
                self._json({"error": f"could not process the recording: {type(exc).__name__}"}, 400)
                return
            self._json(result)

    return Handler


def serve(coach: Coach, port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(("127.0.0.1", port), make_handler(coach))
