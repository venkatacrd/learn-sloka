"""AC-RC-12: pinned download with checksums, from a local file:// mirror (no network)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from typer.testing import CliRunner

from recite_coach import model
from recite_coach.cli import setup_app


@pytest.fixture
def mirror(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("RECITE_COACH_HOME", str(tmp_path / "home"))
    base = tmp_path / "mirror"
    folder = base / model.REPO / "resolve" / model.REVISION
    folder.mkdir(parents=True)
    files = {}
    for name in ("a.onnx", "b.json"):
        data = f"fake {name}".encode()
        (folder / name).write_bytes(data)
        files[name] = hashlib.sha256(data).hexdigest()
    monkeypatch.setattr(model, "FILES", files)
    return base


def test_AC_RC_12_download_verify_and_reuse(mirror: Path) -> None:
    url = f"file://{mirror}"
    assert sorted(model.setup(url, log=None)) == ["a.onnx", "b.json"]
    assert model.missing_or_bad() == []
    assert model.setup(url, log=None) == []  # second run: nothing downloaded
    (model.model_dir() / "a.onnx").write_bytes(b"tampered")
    assert model.missing_or_bad() == ["a.onnx"]
    assert model.setup(url, log=None) == ["a.onnx"]


def test_AC_RC_12_corrupted_download(mirror: Path) -> None:
    (mirror / model.REPO / "resolve" / model.REVISION / "b.json").write_bytes(b"changed upstream")
    with pytest.raises(model.ModelError, match="checksum"):
        model.setup(f"file://{mirror}", log=None)
    assert not (model.model_dir() / "b.json").exists()
    r = CliRunner().invoke(setup_app, ["--base-url", f"file://{mirror}"])
    assert r.exit_code == 2 and "checksum" in r.output
