"""Thin CLI over the pipeline (FR-EX-15). Holds no business logic (constitution 11)."""

from __future__ import annotations

from pathlib import Path

import typer

from sanskrit_extract import __version__
from sanskrit_extract.config import Config, load_config
from sanskrit_extract.ocr import doctor
from sanskrit_extract.ocr.base import OcrEngine
from sanskrit_extract.pages import PageSelection, resolve
from sanskrit_extract.pdf_reader import PdfDocument, PdfError
from sanskrit_extract.pipeline import find_pdfs, plan_pages, run_batch

app = typer.Typer(add_completion=False, help="Extract Devanagari slokas from PDFs into JSONL.")


def _version(value: bool) -> None:
    if value:
        typer.echo(f"sanskrit-extract {__version__}")
        raise typer.Exit()


def parse_pages(spec: str | None) -> PageSelection | None:
    if not spec:
        return None
    try:
        return PageSelection.parse(spec)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--pages") from exc


def make_engine(cfg: Config, psm: int | None = None) -> OcrEngine:
    from sanskrit_extract.ocr.tesseract import TesseractEngine

    return TesseractEngine(cfg.ocr.languages, psm or cfg.ocr.psm, cfg.ocr.cache_dir)


def _ranges(nums: list[int]) -> str:
    """[5, 6, 7, 9] -> '5-7, 9'"""
    out: list[str] = []
    for n in nums:
        if out and out[-1].split("-")[-1] == str(n - 1):
            out[-1] = out[-1].split("-")[0] + f"-{n}"
        else:
            out.append(str(n))
    return ", ".join(out)


@app.command()
def main(
    input_path: Path = typer.Argument(..., exists=True, help="A PDF file or a folder of PDFs."),
    out: Path = typer.Option(Path("extracted"), "-o", "--out", help="Output folder."),
    config: Path | None = typer.Option(None, "--config", exists=True, help="Config TOML."),
    profile: Path | None = typer.Option(None, "--profile", exists=True, help="Segmentation profile TOML."),
    force_ocr: bool = typer.Option(False, "--force-ocr", help="OCR every page."),
    pages: str | None = typer.Option(None, "--pages", help="e.g. 5, 1-10, 1,3-4 or 10- (to the end)"),
    dpi: int | None = typer.Option(None, "--dpi", min=72, help="OCR render DPI (default 300)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Classify pages only; no OCR, no output."),
    verify_ocr: bool = typer.Option(False, "--verify-ocr", help="Cross-check every unit with a second OCR reading."),
    version: bool = typer.Option(False, "--version", callback=_version, is_eager=True),
) -> None:
    """Extract Devanagari slokas from PDFs into JSONL (exit 0 ok, 1 some files failed, 2 bad usage)."""
    cfg = load_config(config, profile)
    cfg.force_ocr = force_ocr
    cfg.verify.enabled = cfg.verify.enabled or verify_ocr
    if dpi:
        cfg.ocr.dpi = dpi
    selected = parse_pages(pages)
    pdfs = find_pdfs(input_path)

    plans: dict[Path, int] = {}
    for pdf in pdfs:
        try:
            with PdfDocument(pdf) as doc:
                page_plans = plan_pages(doc, cfg, selected)
                missing = resolve(selected, doc.page_count)[1]
                if missing:
                    typer.echo(f"note: {pdf.name} has {doc.page_count} pages; pages {_ranges(missing)} skipped")
        except PdfError:
            continue
        plans[pdf] = sum(p.needs_ocr for p in page_plans)
        if dry_run:
            for p in page_plans:
                typer.echo(f"{pdf.name} p{p.number}: {p.page_class.value}{' (OCR)' if p.needs_ocr else ''}")
            typer.echo(f"{pdf.name}: {plans[pdf]} pages need OCR")
    if dry_run:
        raise typer.Exit(0)

    if any(plans.values()) or cfg.verify.enabled:
        check = doctor.check()
        if not check.ok:
            typer.echo(check.message, err=True)
            raise typer.Exit(2)

    result = run_batch(
        input_path, out, cfg, lambda: make_engine(cfg), selected, lambda: make_engine(cfg, cfg.verify.psm)
    )
    for path in result.written:
        typer.echo(f"wrote {path}")
    for name, err in result.failed.items():
        typer.echo(f"FAILED {name}: {err}", err=True)
    raise typer.Exit(1 if result.failed else 0)
