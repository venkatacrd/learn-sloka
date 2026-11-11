"""Running header/footer and page-number removal (FR-EX-08)."""

from __future__ import annotations

import re
import statistics
from collections import Counter

from sanskrit_extract.config import Profile
from sanskrit_extract.models import Line, PageResult

_DIGITS = re.compile(r"[0-9०-९]+")
_BARE_NUMBER = re.compile(r"^\s*[-–]?\s*[0-9०-९ivxlc]+\s*[-–]?\s*$", re.I)
_RULE_TOLERANCE = 2.0  # points


def _key(text: str) -> str:
    return _DIGITS.sub("#", " ".join(text.split()))


def _in_zone(line: Line, page: PageResult, zone: float) -> bool:
    cy = (line.bbox[1] + line.bbox[3]) / 2
    return cy < zone * page.height or cy > (1 - zone) * page.height


def _zone_keys(pages: list[PageResult], profile: Profile) -> list[set[str]]:
    return [{_key(ln.text) for ln in p.lines if _in_zone(ln, p, profile.header_zone)} for p in pages]


def _repeated(keys: list[set[str]], share: float) -> set[str]:
    """Keys found on ≥ share of these pages (needs at least 2 pages)."""
    if len(keys) < 2:
        return set()
    counts: Counter[str] = Counter(k for page in keys for k in page)
    return {k for k, n in counts.items() if n >= max(2, share * len(keys))}


def _common_rule(ys: list[float | None], share: float) -> float | None:
    """A rule height (± tolerance) present on ≥ share of the pages, or None."""
    found = [y for y in ys if y is not None]
    if not found or len(found) < share * len(ys):
        return None
    ref = statistics.median(found)
    near = [y for y in found if abs(y - ref) <= _RULE_TOLERANCE]
    return ref if len(near) >= share * len(ys) else None


def _margin_rules(pages: list[PageResult], profile: Profile) -> tuple[float | None, float | None]:
    """Document-wide header rule (lowest rule in the top zone) and footer rule (highest in the bottom zone)."""
    tops: list[float | None] = []
    bottoms: list[float | None] = []
    for p in pages:
        top = [y for y in p.rules if y < profile.rule_zone * p.height]
        bottom = [y for y in p.rules if y > (1 - profile.rule_zone) * p.height]
        tops.append(max(top) if top else None)
        bottoms.append(min(bottom) if bottom else None)
    return _common_rule(tops, profile.repeat_min_share), _common_rule(bottoms, profile.repeat_min_share)


def _has_rule(page: PageResult, y: float | None) -> bool:
    return y is not None and any(abs(r - y) <= _RULE_TOLERANCE for r in page.rules)


def remove_headers_footers(
    pages: list[PageResult], profile: Profile
) -> tuple[list[PageResult], list[tuple[Line, str]]]:
    """Return pages without header/footer lines, plus each removed line with its reason (for the report)."""
    keys = _zone_keys(pages, profile)
    share = profile.repeat_min_share
    odd = [k for p, k in zip(pages, keys, strict=True) if p.number % 2]
    even = [k for p, k in zip(pages, keys, strict=True) if not p.number % 2]
    # alternating left/right running headers repeat on the odd or the even pages only
    repeated = _repeated(keys, share) | _repeated(odd, share) | _repeated(even, share)
    sizes = [ln.size for p in pages for ln in p.lines if ln.size > 0]
    body = statistics.median(sizes) if sizes else 0.0
    small_counts: Counter[str] = Counter()
    for p in pages:
        small_counts.update(
            {
                _key(ln.text)
                for ln in p.lines
                if _in_zone(ln, p, profile.header_zone) and 0 < ln.size <= profile.small_font_ratio * body
            }
        )
    small_repeated = {k for k, n in small_counts.items() if n >= profile.small_font_min_pages}
    head_rule, foot_rule = _margin_rules(pages, profile)

    removed: list[tuple[Line, str]] = []
    out: list[PageResult] = []
    for page in pages:
        keep: list[Line] = []
        has_head, has_foot = _has_rule(page, head_rule), _has_rule(page, foot_rule)
        for ln in page.lines:
            above = has_head and head_rule is not None and ln.bbox[3] <= head_rule + _RULE_TOLERANCE
            below = has_foot and foot_rule is not None and ln.bbox[1] >= foot_rule - _RULE_TOLERANCE
            # where a page has a separator rule, that rule (not the zone) marks the margin on its side
            cy = (ln.bbox[1] + ln.bbox[3]) / 2
            top_zone = cy < profile.header_zone * page.height and not has_head
            bottom_zone = cy > (1 - profile.header_zone) * page.height and not has_foot
            in_zone = top_zone or bottom_zone
            if (in_zone or above or below) and _BARE_NUMBER.match(ln.text):
                removed.append((ln, "page_number"))
            elif above or below or (in_zone and (_key(ln.text) in repeated or _key(ln.text) in small_repeated)):
                removed.append((ln, "header_footer"))
            else:
                keep.append(ln)
        out.append(PageResult(page.number, page.width, page.height, page.page_class, keep, page.rules))
    return out, removed
