#!/usr/bin/env bash
# Recitation practice page (feature 004): pick a sloka, play the instructor, record yourself, get feedback.
#
#   ./practice.sh [--text <doc>.romanized.jsonl] [--audio <folder>] [--port 8770]
#
# Defaults: text = the first text-outs/*.romanized.jsonl, audio = audio-outs/ (instructor's per-sloka MP3s).
# First run downloads the speech model once (~180 MB, needs internet) into ~/.recite-coach/; after that
# everything runs offline on this Mac. The page opens in your browser; press Ctrl+C here to stop.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
TEXT=""; AUDIO="$ROOT/audio-outs"; PORT=8770
while [[ $# -gt 0 ]]; do
  case $1 in
    --text) TEXT=$2; shift 2 ;;
    --audio) AUDIO=$2; shift 2 ;;
    --port) PORT=$2; shift 2 ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
    *) echo "error: unknown option $1" >&2; exit 2 ;;
  esac
done
if [[ -z "$TEXT" ]]; then
  TEXT=$(ls "$ROOT"/text-outs/*.romanized.jsonl 2>/dev/null | head -1 || true)
  [[ -n "$TEXT" ]] || { echo "error: no text-outs/*.romanized.jsonl — run ./convert-text.sh first, or pass --text" >&2; exit 2; }
fi
[[ -d "$AUDIO" ]] || echo "note: $AUDIO not found — slokas will have no instructor audio (run ./split-audio.sh)"

export UV_NO_EDITABLE=1
unset VIRTUAL_ENV
P=(--project "$ROOT/recitation-coach")
uv run -q "${P[@]}" recite-setup          # downloads the model only if missing or corrupted
exec uv run -q "${P[@]}" recite-serve --text "$TEXT" --audio "$AUDIO" --port "$PORT"
