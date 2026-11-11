"""Startup check for the local Tesseract install (FR-EX-17)."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass

INSTALL_HINT = "brew install tesseract tesseract-lang"
REQUIRED_LANGS = ("san", "hin")


@dataclass(frozen=True)
class DoctorResult:
    ok: bool
    message: str


def check(langs: tuple[str, ...] = REQUIRED_LANGS) -> DoctorResult:
    exe = shutil.which("tesseract")
    if exe is None:
        return DoctorResult(False, f"Tesseract is not installed. Install it with: {INSTALL_HINT}")
    out = subprocess.run([exe, "--list-langs"], capture_output=True, text=True, check=False)
    available = {line.strip() for line in (out.stdout + out.stderr).splitlines()}
    missing = [lang for lang in langs if lang not in available]
    if missing:
        return DoctorResult(
            False, f"Tesseract language model(s) missing: {', '.join(missing)}. Install with: {INSTALL_HINT}"
        )
    return DoctorResult(True, "ok")
