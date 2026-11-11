"""Page selection for --pages: `5`, `1-10`, `1,3-4`, open-ended `10-` (FR-TR-15).

Same syntax as the extractor's --pages; kept separate because the two projects share only the contracts.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PageSelection:
    spec: str
    ranges: tuple[tuple[int, int | None], ...]  # (first, last or None = to the end), 1-based, inclusive

    @classmethod
    def parse(cls, spec: str) -> PageSelection:
        ranges: list[tuple[int, int | None]] = []
        for part in spec.split(","):
            part = part.strip()
            a, dash, b = part.partition("-")
            try:
                start = int(a)
                end = None if dash and not b.strip() else int(b or a)
            except ValueError:
                raise ValueError(f"bad page range: {part!r}") from None
            if start < 1 or (end is not None and end < start):
                raise ValueError(f"bad page range: {part!r}")
            ranges.append((start, end))
        return cls(spec.strip(), tuple(ranges))

    def overlaps(self, page_start: int, page_end: int) -> bool:
        """True if a unit on pages page_start..page_end touches the selection."""
        return any(start <= page_end and (end is None or page_start <= end) for start, end in self.ranges)
