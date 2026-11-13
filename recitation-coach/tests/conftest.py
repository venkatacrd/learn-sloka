from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from recite_coach.compare import HeardChar

ROOT = Path(__file__).resolve().parents[2]
# Outputs of ./convert-chapters.sh (whole book) and ./split-audio.sh (chapter 1), and the author's takes (git-ignored)
TEXT = next(iter(sorted((ROOT / "output/pdf/SrimadBhagawadGeeta_Sanskrit/romanized").glob("*.romanized.jsonl"))), None)
AUDIO = ROOT / "output" / "mp3" / "1_Ch 01 Complete"
TAKES = ROOT / "input" / "recordings"


def heard(text: str, prob: float = 0.95, step: float = 0.05) -> list[HeardChar]:
    """A fake transcription: every character gets its own time slot."""
    return [HeardChar(c, round(i * step, 3), round((i + 1) * step, 3), prob) for i, c in enumerate(text)]


def unit(
    kind: str, lines: list[str], iast: list[str], ref: str | None = None, flags: list[str] | None = None
) -> dict[str, Any]:
    return {
        "extracted": {
            "unit_type": kind,
            "lines": lines,
            "verse_ref": {"normalized": ref} if ref else None,
            "quality": {"flags": flags or []},
        },
        "romanized_lines": {"iast": iast},
    }


@pytest.fixture
def chapter(tmp_path: Path) -> Path:
    rows = [
        unit("heading", ["॥ अथ प्रथमोऽध्यायः ॥"], ["|| atha prathamo'dhyāyaḥ ||"]),
        unit("speaker", ["धृतराष्ट्र उवाच -"], ["dhṛtarāṣṭra uvāca -"]),
        unit(
            "verse",
            ["धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः ।", "मामकाः पाण्डवाश्चैव किमकुर्वत सञ्जय ॥ १ ॥"],
            ["dharmakṣetre kurukṣetre samavetā yuyutsavaḥ |", "māmakāḥ pāṇḍavāścaiva kimakurvata sañjaya || 1 ||"],
            "1",
        ),
        unit("verse", ["हृषीकेशं तदा वाक्यम् इदमाह महीपते ।", "सेनयोरुभयोर्मध्ये रथं स्थापय मेऽच्युत ॥ २१ ॥"],
             ["hṛṣīkeśaṃ tadā vākyam idamāha mahīpate |", "senayorubhayormadhye rathaṃ sthāpaya me'cyuta || 21 ||"],
             "21", ["split_by_speaker"]),
        unit("speaker", ["अर्जुन उवाच -"], ["arjuna uvāca -"]),
    ]  # fmt: skip
    p = tmp_path / "ch.romanized.jsonl"
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    return p


@pytest.fixture
def book(tmp_path: Path) -> Path:
    """Two chapters and a trailing non-chapter part (like the Gita Mahatmya)."""
    v = "धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः ।"
    rows = []
    for ordinal, title, speaker, n in (
        ("प्रथमो", "अर्जुनविषादयोगः", "धृतराष्ट्र उवाच -", 3),
        ("द्वितीयो", "साङ्ख्ययोगः", "सञ्जय उवाच -", 2),
    ):
        rows += [
            unit("heading", [f"॥ अथ {ordinal}ऽध्यायः ॥"], [f"|| atha {ordinal}'dhyāyaḥ ||"]),
            unit("heading", [title], [title + "-iast"]),
            unit("speaker", [speaker], [speaker + "-iast"]),
        ]
        for k in range(1, n + 1):
            rows.append(unit("verse", [v, f"मामकाः पाण्डवाश्चैव ॥ {k} ॥"], ["a |", f"b || {k} ||"], str(k)))
    rows += [
        unit("heading", ["गीतामाहात्म्यम्"], ["gītāmāhātmyam"]),
        unit("verse", [v, "मामकाः ॥ १ ॥"], ["a |", "b || 1 ||"], "1"),
    ]
    p = tmp_path / "book.romanized.jsonl"
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    return p
