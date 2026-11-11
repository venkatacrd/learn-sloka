"""Thin CLI (FR-TR-12). Holds no business logic (constitution 11)."""

from __future__ import annotations

from pathlib import Path

import typer

from sanskrit_romanize import __version__
from sanskrit_romanize.config import SUPPORTED_SCHEMES, load_config
from sanskrit_romanize.engines.base import TransliterationEngine
from sanskrit_romanize.engines.sanscript_engine import SanscriptEngine
from sanskrit_romanize.io import find_inputs, process_file, write
from sanskrit_romanize.pages import PageSelection

app = typer.Typer(add_completion=False, help="Romanize extracted Devanagari JSONL to IAST.")


def _version(value: bool) -> None:
    if value:
        typer.echo(f"sanskrit-romanize {__version__}")
        raise typer.Exit()


@app.command()
def main(
    input_path: Path = typer.Argument(..., exists=True, help="An extractor .jsonl file or a folder of them."),
    out: Path = typer.Option(Path("romanized"), "-o", "--out", help="Output folder."),
    pages: str | None = typer.Option(
        None, "--pages", help="Only units on these source pages: 5, 1-10, 1,3-4 or 10- (to the end)."
    ),
    sloka_files: bool = typer.Option(False, "--sloka-files", help="Also write one .txt per sloka to <out>/slokas/."),
    sloka_prefix: str | None = typer.Option(
        None, "--sloka-prefix", help="File name start for sloka files (implies --sloka-files), e.g. ch01_sloka_."
    ),
    sloka_no_source: bool = typer.Option(
        False, "--sloka-no-source", help="Sloka files without the Devanagari source text (IAST only)."
    ),
    schemes: str = typer.Option("iast", "--schemes", help=f"Comma list from: {', '.join(SUPPORTED_SCHEMES)}"),
    config: Path | None = typer.Option(None, "--config", exists=True, help="Config TOML."),
    cross_check: bool = typer.Option(False, "--cross-check", help="Compare with aksharamukha (extra 'crosscheck')."),
    strict: bool = typer.Option(False, "--strict", help="Exit 1 if any unit fails the round-trip check."),
    version: bool = typer.Option(False, "--version", callback=_version, is_eager=True),
) -> None:
    """Romanize extractor output (exit 0 ok, 1 some input failed, 2 bad usage)."""
    try:
        selection = PageSelection.parse(pages) if pages else None
    except ValueError as exc:
        typer.echo(f"--pages: {exc}", err=True)
        raise typer.Exit(2) from exc
    cfg = load_config(config)
    cfg.schemes = [s.strip() for s in schemes.split(",") if s.strip()]
    bad = [s for s in cfg.schemes if s not in SUPPORTED_SCHEMES]
    if bad:
        typer.echo(f"unknown scheme(s): {', '.join(bad)}", err=True)
        raise typer.Exit(2)
    cross: TransliterationEngine | None = None
    if cross_check or cfg.cross_check:
        from sanskrit_romanize.engines.aksharamukha_engine import AksharamukhaEngine

        cross = AksharamukhaEngine()
    engine = SanscriptEngine()
    failed = False
    wants_slokas = sloka_files or sloka_no_source
    prefix = sloka_prefix if sloka_prefix is not None else ("sloka_" if wants_slokas else None)
    inputs = find_inputs(input_path)
    for path in inputs:
        try:
            result = process_file(path, cfg, engine, cross, selection)
        except Exception as exc:
            typer.echo(f"FAILED {path}: {type(exc).__name__}: {exc}", err=True)
            failed = True
            continue
        # several input files: one sloka folder per document so names cannot clash
        sloka_dir = out / "slokas" / result.doc_id if len(inputs) > 1 else out / "slokas"
        written = write(out, result, prefix, sloka_dir, sloka_source=not sloka_no_source)
        for p in written:
            if p.parent != sloka_dir:
                typer.echo(f"wrote {p}")
        block = result.report.get("sloka_files")
        if block:
            if block.get("error"):
                nums = ", ".join(map(str, block["duplicate_numbers"]))
                typer.echo(
                    f"{path.name}: no sloka files: sloka numbers repeat ({nums}); pick one chapter with --pages",
                    err=True,
                )
                failed = True
            else:
                typer.echo(f"wrote {block['written']} sloka files to {sloka_dir} ({prefix}NN.txt)")
        rep = result.report
        note = f" ({rep['units_outside_pages']} outside --pages skipped)" if selection else ""
        typer.echo(
            f"{path.name}: {rep['units_out']} units, round-trip OK {rep['roundtrip_ok']}/{rep['units_out']}{note}"
        )
        if result.invalid:
            typer.echo(f"{path.name}: {len(result.invalid)} invalid input line(s), see report", err=True)
            failed = True
        if strict and rep["roundtrip_failures"]:
            failed = True
    raise typer.Exit(1 if failed else 0)
