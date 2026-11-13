#!/usr/bin/env bash
# Chanted recitation MP3(s) → one MP3 per sloka (feature 003, specs/003-audio-splitter/).
#
#   ./split-audio.sh [<mp3-or-folder>] [output-dir] [-- extra options, e.g. --expected 47]
#   ./split-audio.sh "1_Ch 01 Complete.mp3" -- --expected 47 \
#       --text output/pdf/01_Chapter_Sanskrit/romanized/<doc>.romanized.jsonl
#   ./split-audio.sh "1_Ch 11 Complete.mp3" -- --name CH11 --expected 55   # files CH11_sloka_01.mp3 …
#
# Input: recordings live in input/mp3/. A bare file name is looked up there; no input = every MP3 in input/mp3/.
# Output: output/mp3/<recording name>/, one folder per recording, unless an output folder is given.
# The output folder is emptied before every run.
# Output per input file:
#   <name>_intro.mp3, <name>_sloka_01.mp3 … <name>_sloka_NN.mp3, <name>_closing.mp3
#   <name>.splits.json   cut points and checks
#   <name>.labels.txt    Audacity labels: open the original, File › Import › Labels, to review the cuts
#   <name>.review.html   open in a browser to check every cut by ear (--text adds each sloka's lines)
# Exit code is non-zero if the split looks doubtful (see the warnings it prints).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
INBOX="$ROOT/input/mp3"
POS=()
while [[ $# -gt 0 && "$1" != -* ]]; do POS+=("$1"); shift; done
[[ "${1:-}" == "--" ]] && shift
# "$@" now holds the extra sloka-split options
if [[ ${#POS[@]} -lt 1 ]]; then
  [[ -d "$INBOX" ]] || { sed -n '2,17p' "$0"; exit 2; }
  POS=("$INBOX")
fi
ARG="${POS[0]}"
[[ ! -e "$ARG" && -e "$INBOX/$ARG" ]] && ARG="$INBOX/$ARG"
[[ -e "$ARG" ]] || { echo "error: ${POS[0]} not found (recordings go in input/mp3/)" >&2; exit 2; }

# A folder and no output folder: one run per recording, each into its own output/mp3/<name>/ folder.
if [[ -d "$ARG" && ${#POS[@]} -lt 2 ]]; then
  shopt -s nullglob; MP3S=("$ARG"/*.[mM][pP]3); shopt -u nullglob
  [[ ${#MP3S[@]} -gt 0 ]] || { echo "error: no MP3 in $ARG" >&2; exit 2; }
  ALL=0
  for f in "${MP3S[@]}"; do
    echo "==== $(basename "$f")"
    "$0" "$f" -- "$@" || ALL=1
  done
  exit $ALL
fi
IN="$(cd "$(dirname "$ARG")" && pwd)/$(basename "$ARG")"
NAME="$(basename "$IN")"; NAME="${NAME%.*}"
OUT="${POS[1]:-$ROOT/output/mp3/$NAME}"
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"

export UV_NO_EDITABLE=1
unset VIRTUAL_ENV
echo "== split: $IN -> $OUT"
# --project instead of cd, so relative paths in the extra options (e.g. --text) still work
uv run -q --project "$ROOT/audio-splitter" sloka-split "$IN" -o "$OUT" --clean "$@"
