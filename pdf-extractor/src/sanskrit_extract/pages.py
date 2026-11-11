"""Page selection: `5`, `1-10`, `1,3-4`, open-ended `10-` (FR-EX-21)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PageSelection:
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
        if not ranges:
            raise ValueError("empty page range")
        return cls(tuple(ranges))

    def resolve(self, page_count: int) -> tuple[list[int], list[int]]:
        """(selected pages that exist, selected pages the document does not have)."""
        wanted: set[int] = set()
        for start, end in self.ranges:
            wanted.update(range(start, (end if end is not None else max(page_count, start)) + 1))
        return sorted(p for p in wanted if p <= page_count), sorted(p for p in wanted if p > page_count)


Pages = PageSelection | list[int] | None


def resolve(pages: Pages, page_count: int) -> tuple[list[int] | None, list[int]]:
    """Normalize any page argument: (pages to read or None for all, missing pages)."""
    if pages is None:
        return None, []
    if isinstance(pages, PageSelection):
        return pages.resolve(page_count)
    return sorted({p for p in pages if 1 <= p <= page_count}), sorted({p for p in pages if p > page_count})
