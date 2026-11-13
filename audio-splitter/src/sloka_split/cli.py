"""sloka-split CLI (FR-AS-12). No business logic here."""

from __future__ import annotations

from pathlib import Path

import typer

from . import __version__
from .analysis import Settings
from .mp3frames import Mp3Error
from .splitter import BadNameError, UnsafeOutputError, split_path

app = typer.Typer(add_completion=False, help="Split a chanted recitation MP3 into one MP3 per sloka.")


def _version(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.command()
def main(
    input: Path = typer.Argument(..., help="An .mp3 file or a folder of them."),
    out: Path = typer.Option(Path("audio-outs"), "-o", "--out", help="Output folder."),
    clean: bool = typer.Option(False, "--clean", help="Delete everything in the output folder first."),
    expected: int | None = typer.Option(None, "--expected", help="Expected sloka count; mismatch exits 1."),
    half_verses: int = typer.Option(2, "--half-verses-per-sloka", min=1),
    half_verse_end: str = typer.Option(
        "auto", "--half-verse-end", help="Which line ends a half-verse: auto (from pauses), cadence, next."
    ),
    text: Path | None = typer.Option(
        None, "--text", help="Feature-002 .romanized.jsonl: show each sloka's text on the review page."
    ),
    name: str | None = typer.Option(
        None, "--name", help="Start of the output file names, e.g. CH11 → CH11_sloka_01.mp3 (default: the MP3's name)."
    ),
    silence_drop_db: float = typer.Option(20.0, "--silence-drop-db", help="Silence = median level minus this."),
    min_gap: float = typer.Option(0.3, "--min-gap", help="Shortest pause (s) that separates segments."),
    version: bool = typer.Option(False, "--version", callback=_version, is_eager=True),
) -> None:
    if half_verse_end not in ("auto", "cadence", "next"):
        typer.echo("error: --half-verse-end must be auto, cadence or next", err=True)
        raise typer.Exit(2)
    settings = Settings(
        silence_drop_db=silence_drop_db,
        min_gap_s=min_gap,
        half_verses_per_sloka=half_verses,
        half_verse_end=half_verse_end,  # type: ignore[arg-type]
    )
    try:
        results = split_path(input, out, clean=clean, settings=settings, expected=expected, text_path=text, name=name)
    except (UnsafeOutputError, BadNameError, FileNotFoundError, Mp3Error) as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(2) from e
    if not results:
        typer.echo(f"error: no .mp3 files in {input}", err=True)
        raise typer.Exit(2)
    for r in results:
        extra = sorted({p.kind for p in r.parts} - {"sloka"})
        note = f" (+ {', '.join(extra)})" if extra else ""
        warn = f"  warnings: {', '.join(r.warnings)}" if r.warnings else ""
        typer.echo(f"{r.source.name}: {r.sloka_count} slokas{note} -> {out}{warn}")
    if any(r.doubtful for r in results):
        raise typer.Exit(1)
