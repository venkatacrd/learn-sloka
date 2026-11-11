#!/usr/bin/env bash
# Chanted recitation MP3(s) → one MP3 per sloka (feature 003, specs/003-audio-splitter/).
#
#   ./split-audio.sh <mp3-or-folder> [output-dir] [-- extra options, e.g. --expected 47]
#   ./split-audio.sh "1_Ch 01 Complete.mp3" -- --expected 47 --text text-outs/<doc>.romanized.jsonl
#
# The output folder (default: audio-outs/ next to this script) is emptied before every run.
# Output per input file:
#   <name>_intro.mp3, <name>_sloka_01.mp3 … <name>_sloka_NN.mp3, <name>_closing.mp3
#   <name>.splits.json   cut points and checks
#   <name>.labels.txt    Audacity labels: open the original, File › Import › Labels, to review the cuts
#   <name>.review.html   open in a browser to check every cut by ear (--text adds each sloka's lines)
# Exit code is non-zero if the split looks doubtful (see the warnings it prints).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
if [[ $# -lt 1 ]]; then sed -n '2,13p' "$0"; exit 2; fi
IN="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
shift
OUT="$ROOT/audio-outs"
if [[ $# -ge 1 && "$1" != -* ]]; then OUT="$1"; shift; fi
[[ "${1:-}" == "--" ]] && shift
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"

export UV_NO_EDITABLE=1
unset VIRTUAL_ENV
# --project instead of cd, so relative paths in the extra options (e.g. --text) still work
uv run -q --project "$ROOT/audio-splitter" sloka-split "$IN" -o "$OUT" --clean "$@"
