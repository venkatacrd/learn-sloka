"""Feedback for the learner: IAST, plain-English sentences, JSON shape (FR-RC-10)."""

from __future__ import annotations

from typing import Any

from indic_transliteration import sanscript

from .compare import Comparison, Finding, strip_common

_CONSONANTS = set("कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसहळ")
_MATRAS = set("ािीुूृॄेैोौॢॣ")
_SPECIAL = {"ं": "ṃ", "ः": "ḥ", "ँ": "m̐", "्": ""}
_DESC = {
    "ṭ": "retroflex — tongue curled back", "ṭh": "retroflex", "ḍ": "retroflex — tongue curled back", "ḍh": "retroflex",
    "ṇ": "retroflex", "t": "dental — tongue at the teeth", "th": "dental", "d": "dental — tongue at the teeth",
    "dh": "dental", "n": "dental", "ś": "palatal, as in 'sh'", "ṣ": "retroflex, tongue curled back",
    "s": "dental, as in 'see'",
}  # fmt: skip


def iast(dev: str) -> str:
    return str(sanscript.transliterate(dev, sanscript.DEVANAGARI, sanscript.IAST))


def letters_iast(dev: str) -> str:
    """Devanagari fragment -> IAST without inherent vowels: 'ड' -> 'ḍ', 'ा' -> 'ā', 'ञ्' -> 'ñ'."""
    out = []
    for c in dev:
        if c in _SPECIAL:
            out.append(_SPECIAL[c])
        elif c in _CONSONANTS:
            out.append(iast(c + "्"))
        elif c in _MATRAS:
            out.append(iast("क" + c)[1:])
        else:
            out.append(iast(c))
    return "".join(out) or "∅"


def _core(f: Finding) -> tuple[str, str]:
    return strip_common(f.expected, f.heard)


def sentence(f: Finding, word_iast: str, heard_iast: str) -> str:
    r, h = _core(f)
    ri, hi = letters_iast(r), letters_iast(h)
    w = f"*{word_iast}*"
    heard = f" (heard *{heard_iast}*)" if heard_iast and heard_iast != word_iast else ""
    if f.kind == "vowel length":
        long_expected = any(c in "ाीूॄआईऊ" for c in r)
        ri, hi = (ri if r else "a"), (hi if h else "a")
        return (
            f"{w}: the vowel should be long (**{ri}**), it sounded short (**{hi}**){heard}"
            if long_expected
            else f"{w}: the vowel should be short (**{ri}**), it sounded long (**{hi}**){heard}"
        )
    if f.kind in ("retroflex/dental", "sibilant"):
        rd, hd = _DESC.get(ri.strip(), ""), _DESC.get(hi.strip(), "")
        return f"{w}: heard **{hi}** ({hd}) instead of **{ri}** ({rd}){heard}"
    if f.kind == "aspiration":
        asp = "h" in ri
        return (
            f"{w}: **{ri}** needs a breath of air (aspirated); heard **{hi}**{heard}"
            if asp
            else f"{w}: **{ri}** has no breath (unaspirated); heard **{hi}**{heard}"
        )
    if f.kind == "voicing":
        return f"{w}: heard **{hi}** instead of **{ri}**{heard}"
    if f.kind == "nasal":
        if not h:
            return f"{w}: the nasal **{ri}** is missing{heard}"
        return f"{w}: nasal sound — expected **{ri}**, heard **{hi}**{heard}"
    if f.kind == "visarga":
        return f"{w}: check the visarga (**ḥ**) at the end — not clearly heard (the model is unsure about ḥ)"
    if f.kind == "missing word":
        return f"{w}: this word was not heard"
    if f.kind == "extra word":
        return f"extra sounds **{hi}** heard near {w}"
    if f.kind == "missing letter":
        return f"{w}: **{ri}** is missing{heard}"
    if f.kind == "extra letter":
        return f"{w}: extra **{hi}**{heard}"
    return f"{w}: heard **{hi}** instead of **{ri}**{heard}"


def to_json(c: Comparison, sloka: int, teacher: Comparison | None = None) -> dict[str, Any]:
    tspan = {(w.line, w.pos): w.span for w in teacher.words} if teacher else {}
    lines: dict[int, dict[str, Any]] = {}
    for w in c.words:
        pada = c.lines[w.line].pada if c.lines else 0
        line = lines.setdefault(w.line, {"index": w.line, "pada": pada, "speaker": w.speaker, "words": []})
        line["words"].append(
            {
                "pos": w.pos,
                "dev": w.word.dev,
                "iast": w.word.iast,
                "status": w.status,
                "heard_dev": w.heard,
                "heard_iast": iast(w.heard) if w.heard else "",
                "span": w.span,
                "teacher_span": tspan.get((w.line, w.pos)),
            }
        )
    findings = []
    for f in c.findings:
        w = c.words[f.word]
        heard_iast = iast(w.heard) if w.heard else ""
        r, h = _core(f)
        findings.append(
            {
                "kind": f.kind,
                "line": w.line,
                "pada": c.lines[w.line].pada if c.lines else 0,
                "pos": w.pos,
                "word_dev": w.word.dev,
                "word_iast": w.word.iast,
                "expected": r,
                "heard": h,
                "expected_iast": letters_iast(r),
                "heard_iast": letters_iast(h),
                "confidence": f.confidence,
                "reported": f.reported,
                "message": sentence(f, w.word.iast, heard_iast),
                "span": w.span,
                "teacher_span": tspan.get((w.line, w.pos)),
            }
        )
    return {
        "sloka": sloka,
        "score": c.score,
        "heard": c.heard.strip(),
        "speaker_compared": c.speaker_compared,
        "lines": [lines[k] for k in sorted(lines)],
        "findings": findings,
        "counts": {
            "reported": sum(1 for f in c.findings if f.reported),
            "unsure": sum(1 for f in c.findings if not f.reported),
        },
    }
