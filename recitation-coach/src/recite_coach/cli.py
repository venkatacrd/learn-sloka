"""Thin CLIs: recite-check, recite-setup, recite-serve (FR-RC-12, 13). No business logic here."""

from __future__ import annotations

import json
import threading
import webbrowser
from pathlib import Path

import typer

from . import __version__
from .coach import Coach, UnknownSloka
from .model import DEFAULT_BASE_URL, ModelError, load_audio, model_dir, setup

check_app = typer.Typer(add_completion=False, help="Check one recitation of a sloka and print pronunciation feedback.")
setup_app = typer.Typer(add_completion=False, help="Download and verify the speech model (once; needs internet).")
serve_app = typer.Typer(add_completion=False, help="Start the local practice page.")

TEXT_HELP = "The converter's <doc>.romanized.jsonl for the chapter."
AUDIO_HELP = "Folder with the instructor's <name>_sloka_NN.mp3 files (from split-audio)."


def _version(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


def _open(text: Path, audio: Path | None) -> Coach:
    try:
        return Coach.open(text, audio)
    except ModelError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(2) from exc
    except OSError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(2) from exc


@check_app.command()
def check(
    recording: Path = typer.Argument(..., exists=True, dir_okay=False, help="WAV / MP3 / FLAC recording."),
    sloka: int = typer.Option(..., "--sloka", min=1),
    text: Path = typer.Option(..., "--text", exists=True, help=TEXT_HELP),
    audio: Path | None = typer.Option(None, "--audio", help=AUDIO_HELP),
    as_json: bool = typer.Option(False, "--json", help="Print the feedback as JSON."),
    show_unsure: bool = typer.Option(False, "--show-unsure", help="Also list findings the model is unsure about."),
    version: bool = typer.Option(False, "--version", callback=_version, is_eager=True),
) -> None:
    """Exit 0 = no mistakes reported, 1 = mistakes reported, 2 = usage / IO error."""
    coach = _open(text, audio)
    try:
        result = coach.check(sloka, load_audio(recording))
    except UnknownSloka:
        typer.echo(f"error: sloka {sloka} not found in {text.name}", err=True)
        raise typer.Exit(2) from None
    except Exception as exc:
        typer.echo(f"error: cannot read {recording}: {exc}", err=True)
        raise typer.Exit(2) from exc
    if as_json:
        typer.echo(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"sloka {sloka}: score {result['score']}%  heard: {result['heard']}")
        for f in result["findings"]:
            if f["reported"] or show_unsure:
                tag = "" if f["reported"] else " (unsure)"
                where = f"line {f['pada']}" if f["pada"] else "speaker line"
                typer.echo(f"  {where}: {f['message'].replace('**', '').replace('*', '')}{tag}")
        if not result["counts"]["reported"]:
            typer.echo("  no mistakes reported")
    raise typer.Exit(1 if result["counts"]["reported"] else 0)


@setup_app.command()
def run_setup(
    base_url: str = typer.Option(DEFAULT_BASE_URL, "--base-url", help="Mirror to download from."),
    version: bool = typer.Option(False, "--version", callback=_version, is_eager=True),
) -> None:
    try:
        fetched = setup(base_url, log=typer.echo)
    except ModelError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(2) from exc
    typer.echo(f"model ready in {model_dir()}" + ("" if fetched else " (already downloaded, checksums OK)"))


@serve_app.command()
def run_serve(
    text: Path = typer.Option(..., "--text", exists=True, help=TEXT_HELP),
    audio: Path | None = typer.Option(None, "--audio", help=AUDIO_HELP),
    port: int = typer.Option(8770, "--port"),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="Open the page in the browser."),
    version: bool = typer.Option(False, "--version", callback=_version, is_eager=True),
) -> None:
    from .server import serve

    coach = _open(text, audio)
    try:
        httpd = serve(coach, port)
    except OSError as exc:
        typer.echo(f"error: cannot listen on 127.0.0.1:{port}: {exc}", err=True)
        raise typer.Exit(2) from exc
    url = f"http://127.0.0.1:{port}/"
    n = sum(1 for s in coach.slokas.values() if s.available)
    typer.echo(f"practice page: {url}  ({n} slokas with instructor audio; Ctrl+C to stop)")
    if open_browser:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        typer.echo("stopped")
    finally:
        httpd.server_close()
