"""Configuration (TOML, all keys optional)."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

SUPPORTED_SCHEMES = ("iast", "iso15919", "hk", "itrans", "slp1", "velthuis", "ascii", "telugu")  # telugu: FR-TR-19


class Config(BaseModel):
    schemes: list[str] = Field(default_factory=lambda: ["iast"])  # Q4: IAST only by default
    danda_style: Literal["pipe", "devanagari", "period"] = "pipe"  # FR-TR-05
    digits: Literal["ascii", "devanagari"] = "ascii"  # FR-TR-04
    embedding_text: Literal["iast", "devanagari"] = "iast"  # FR-TR-09
    cross_check: bool = False  # FR-TR-10


def load_config(path: Path | None) -> Config:
    if path is None:
        return Config()
    return Config.model_validate(tomllib.loads(path.read_text(encoding="utf-8")))
