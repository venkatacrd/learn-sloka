"""Compare what was heard with the sloka text: findings, kinds, confidence, score (FR-RC-06, 07, 08)."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .library import Line, Word
from .normalize import VIRAMA, Chars, chars_of, comparison_form, text_of

REPORT_MIN_PROB = 0.4  # tuned 2026-11-11: instructor's 47 correct slokas 0.74 reported/sloka (target <= 1)
# accepted pronunciations (FR-RC-09 seed): (expected letters, heard letters) that are not mistakes
ACCEPTED = [("र्य", "र्ज")]  # य after र said as ज (ācārya ~ ācārja), the reference reciter's own pronunciation


def accepted(r: str, h: str, line_end: bool) -> bool:
    """Differences that are not mistakes: listed variants, and a held final vowel at the end of a line."""
    if any(er in r and r.replace(er, eh) == h for er, eh in ACCEPTED):
        return True
    core_r, core_h = strip_common(r, h)
    return line_end and core_r == "" and core_h == "ा" and h.endswith("ा")  # chanting holds the last vowel


# dependent signs: never start a letter on their own
SIGNS = set("ािीुूृॄेैोौॢॣ्ंःँ़")
VISARGA = "ः"
NASALS = set("ङञणनमं")
_LONG_SHORT = {("ा", ""), ("ी", "ि"), ("ू", "ु"), ("आ", "अ"), ("ई", "इ"), ("ऊ", "उ"), ("ॄ", "ृ")}
_PAIRS = {
    "retroflex/dental": [("ट", "त"), ("ठ", "थ"), ("ड", "द"), ("ढ", "ध"), ("ण", "न")],
    "sibilant": [("श", "ष"), ("श", "स"), ("ष", "स")],
    "aspiration": [
        ("क", "ख"), ("ग", "घ"), ("च", "छ"), ("ज", "झ"), ("ट", "ठ"),
        ("ड", "ढ"), ("त", "थ"), ("द", "ध"), ("प", "फ"), ("ब", "भ"),
    ],
    "voicing": [("क", "ग"), ("च", "ज"), ("ट", "ड"), ("त", "द"), ("प", "ब"), ("ख", "घ"), ("थ", "ध"), ("फ", "भ")],
}  # fmt: skip


@dataclass(frozen=True)
class HeardChar:
    char: str
    start: float  # seconds
    end: float
    prob: float  # model probability of the token this character came from


@dataclass
class Finding:
    kind: str
    line: int  # index into the compared lines
    word: int  # global word index
    expected: str  # Devanagari (the letters that differ, with the letter they belong to)
    heard: str
    confidence: float
    reported: bool  # False = "unsure"
    span: tuple[float, float] | None  # learner time of the word


@dataclass
class WordResult:
    line: int
    pos: int  # position in its line
    index: int  # global word index
    word: Word
    speaker: bool
    status: str = "ok"  # ok | finding | unsure
    span: tuple[float, float] | None = None
    heard: str = ""  # Devanagari letters heard for this word (comparison form)


@dataclass
class Comparison:
    score: float  # % of expected letters said as expected
    words: list[WordResult]
    findings: list[Finding]
    heard: str
    speaker_compared: bool
    edits: int = 0
    lines: list[Line] = field(default_factory=list)


def _sub_cost(x: str, y: str) -> float:
    """Substitution cost: a vowel sign never stands in for a consonant cheaply (so वेता/वदा aligns as
    'े missing' + 'त→द', not 'े→द' + 'त missing')."""
    if x == y:
        return 0.0
    return 1.0 if (x in SIGNS) == (y in SIGNS) else 1.6


def _align(a: str, b: str) -> list[tuple[int | None, int | None]]:
    """Weighted Levenshtein alignment: (index in a or None, index in b or None)."""
    n, m = len(a), len(b)
    D = np.zeros((n + 1, m + 1), dtype=np.float64)
    D[:, 0] = np.arange(n + 1)
    D[0, :] = np.arange(m + 1)
    for i in range(1, n + 1):
        ai = a[i - 1]
        row, prev = D[i], D[i - 1]
        for j in range(1, m + 1):
            row[j] = min(prev[j] + 1, row[j - 1] + 1, prev[j - 1] + _sub_cost(ai, b[j - 1]))
    i, j = n, m
    out: list[tuple[int | None, int | None]] = []
    while i or j:
        if i and j and abs(D[i, j] - (D[i - 1, j - 1] + _sub_cost(a[i - 1], b[j - 1]))) < 1e-9:
            out.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif i and abs(D[i, j] - (D[i - 1, j] + 1)) < 1e-9:
            out.append((i - 1, None))
            i -= 1
        else:
            out.append((None, j - 1))
            j -= 1
    return out[::-1]


def strip_common(r: str, h: str) -> tuple[str, str]:
    while r and h and r[0] == h[0]:
        r, h = r[1:], h[1:]
    while r and h and r[-1] == h[-1]:
        r, h = r[:-1], h[:-1]
    return r, h


def _letters(s: str) -> int:
    return sum(1 for c in s if c != VIRAMA)


def classify(r: str, h: str) -> str:
    """Kind of difference between expected letters r and heard letters h (FR-RC-07)."""
    r, h = strip_common(r, h)
    if VISARGA in r and VISARGA not in h:
        return "visarga"  # dropped visarga: the model's weak spot, always "unsure"
    if (r, h) in _LONG_SHORT or (h, r) in _LONG_SHORT:
        return "vowel length"
    rc, hc = r.replace(VIRAMA, ""), h.replace(VIRAMA, "")
    if len(rc) == 1 and len(hc) == 1:
        for kind, pairs in _PAIRS.items():
            if (rc, hc) in pairs or (hc, rc) in pairs:
                return kind
    if (rc or hc) and set(rc + hc) <= NASALS:
        return "nasal"
    if not h:
        return "missing letter"
    if not r:
        return "extra letter"
    return "substituted letter"


def _regions(ops: list[tuple[int | None, int | None]], ref: str, hyp: str) -> list[tuple[int, int]]:
    """Runs of differing ops, widened to whole letters (a region never starts on a dependent sign and takes the
    signs that follow it)."""
    diff = [not (ri is not None and hi is not None and ref[ri] == hyp[hi]) for ri, hi in ops]

    def ch(op: tuple[int | None, int | None]) -> str:
        ri, hi = op
        return ref[ri] if ri is not None else (hyp[hi] if hi is not None else "")

    def starts_letter(k: int) -> bool:  # consonant / independent vowel not joined to the previous one by a virama
        return ch(ops[k]) not in SIGNS and (k == 0 or ch(ops[k - 1]) != VIRAMA)

    runs: list[tuple[int, int]] = []
    k = 0
    while k < len(ops):
        if not diff[k]:
            k += 1
            continue
        a = k
        k += 1
        while k < len(ops) and diff[k] and not starts_letter(k):  # one run per letter
            k += 1
        runs.append((a, k))
    out: list[tuple[int, int]] = []
    for a, b in runs:
        while a > 0 and (ch(ops[a]) in SIGNS or ch(ops[a - 1]) == VIRAMA):
            a -= 1
        while b < len(ops) and ch(ops[b]) in SIGNS:
            b += 1
        if out and a < out[-1][1]:
            out[-1] = (out[-1][0], max(b, out[-1][1]))
        else:
            out.append((a, b))
    return out


def _expected_chars(lines: list[Line], include_speaker: bool) -> tuple[Chars, list[WordResult]]:
    chars: Chars = []
    words: list[WordResult] = []
    for li, line in enumerate(lines):
        if line.speaker and not include_speaker:
            continue
        for pos, w in enumerate(line.words):
            g = len(words)
            words.append(WordResult(li, pos, g, w, line.speaker))
            chars += chars_of(w.dev, g)
    return comparison_form(chars), words


def compare(lines: list[Line], heard: list[HeardChar], report_min_prob: float = REPORT_MIN_PROB) -> Comparison:
    """Compare a transcription with the sloka; the speaker line is optional (best match is kept)."""
    hchars = comparison_form([(c.char, i) for i, c in enumerate(heard)])
    hyp = text_of(hchars)
    best: tuple[int, Chars, list[WordResult], list[tuple[int | None, int | None]], bool] | None = None
    options = [True, False] if any(line.speaker for line in lines) else [True]
    for with_speaker in options:
        rchars, words = _expected_chars(lines, with_speaker)
        ops = _align(text_of(rchars), hyp)
        edits = sum(1 for ri, hi in ops if ri is None or hi is None or rchars[ri][0] != hchars[hi][0])
        if best is None or edits < best[0]:
            best = (edits, rchars, words, ops, with_speaker)
    assert best is not None
    edits, rchars, words, ops, with_speaker = best
    ref = text_of(rchars)
    word_len: dict[int, int] = {}
    for _, o in rchars:
        word_len[o] = word_len.get(o, 0) + 1

    def heard_span(idx: list[int]) -> tuple[float, float] | None:
        hs = [heard[hchars[i][1]] for i in idx]
        return (min(h.start for h in hs), max(h.end for h in hs)) if hs else None

    # learner time span of each word from the heard letters aligned to it
    per_word: dict[int, list[int]] = {}
    for ri, hi in ops:
        if ri is not None and hi is not None:
            per_word.setdefault(rchars[ri][1], []).append(hi)
    for w in words:
        w.span = heard_span(per_word.get(w.index, []))
    # heard letters per word; an inserted letter belongs to the word of the expected letter before it
    owner = 0
    for ri, hi in ops:
        if ri is not None:
            owner = rchars[ri][1]
        if hi is not None:
            words[owner].heard += hyp[hi]

    # expected index of the last letter of each line (where a held vowel is chanting, not a mistake)
    end_of_line: dict[int, int] = {}
    for i, (_, o) in enumerate(rchars):
        end_of_line[words[o].line] = i  # indices increase, so the last one wins
    line_end = set(end_of_line.values())

    findings: list[Finding] = []
    for a, b in _regions(ops, ref, hyp):
        seg = ops[a:b]
        r = "".join(ref[ri] for ri, _ in seg if ri is not None)
        h = "".join(hyp[hi] for _, hi in seg if hi is not None)
        if r == h:
            continue
        at_end = any(ri in line_end for ri, _ in seg if ri is not None)
        if accepted(r, h, at_end):
            continue
        owners = [rchars[ri][1] for ri, _ in seg if ri is not None]
        if not owners:  # pure insertion: attach to the expected letter before it (or after)
            before = [rchars[ri][1] for ri, _ in ops[:a] if ri is not None]
            after = [rchars[ri][1] for ri, _ in ops[b:] if ri is not None]
            owners = before[-1:] or after[:1] or [0]
        word = owners[0]
        his = [hi for _, hi in seg if hi is not None]
        if his:
            conf = min(heard[hchars[hi][1]].prob for hi in his)
        else:  # deletion: how sure was the model about the letters around the gap
            near = [hi for _, hi in ops[max(0, a - 1) : a] + ops[b : b + 1] if hi is not None]
            conf = min((heard[hchars[hi][1]].prob for hi in near), default=0.0)
        kind = classify(r, h)
        core_r, core_h = strip_common(r, h)
        reported = kind != "visarga" and (conf >= report_min_prob or max(_letters(core_r), _letters(core_h)) >= 2)
        if not r and _letters(h) >= 3:
            kind = "extra word"
        findings.append(Finding(kind, words[word].line, word, r, h, round(conf, 3), reported, words[word].span))
        status = "finding" if reported else "unsure"
        for o in set(owners):
            if words[o].status != "finding":
                words[o].status = status
    # a word whose letters were (almost) all not heard is one "missing word" finding, not one per letter
    matched_per_word: dict[int, int] = {}
    for ri, hi in ops:
        if ri is not None and hi is not None and ref[ri] == hyp[hi]:
            matched_per_word[rchars[ri][1]] = matched_per_word.get(rchars[ri][1], 0) + 1
    for w in words:
        if w.index in word_len and matched_per_word.get(w.index, 0) <= word_len[w.index] // 3:
            findings = [f for f in findings if f.word != w.index]
            findings.append(Finding("missing word", w.line, w.index, w.word.dev, "", 1.0, True, w.span))
            w.status = "finding"
    findings.sort(key=lambda f: (f.line, f.word))
    matched = sum(1 for ri, hi in ops if ri is not None and hi is not None and ref[ri] == hyp[hi])
    score = round(100.0 * matched / max(len(ref), 1), 1)
    return Comparison(score, words, findings, "".join(c.char for c in heard), with_speaker, edits, lines)
