#!/usr/bin/env bash
# Recitation practice page (feature 004): pick a sloka, play the instructor, record yourself, get feedback.
#
#   ./practice.sh [--text <pdf name> | <file.romanized.jsonl>] [--audio <recording name> | <folder>] [--port 8770]
#   ./practice.sh                                   # the book in output/pdf/ + every chapter in output/mp3/
#   ./practice.sh --audio "1_Ch 02 Complete"        # only chapter 2's instructor audio
#
# --text NAME  = the converted text in output/pdf/NAME/romanized/ (./convert-chapters.sh or ./convert.sh);
#                a whole book gives a chapter picker on the page
# --audio NAME = one recording's per-sloka MP3s in output/mp3/NAME/ (./split-audio.sh); default: all of output/mp3/,
#                each folder matched to its chapter by the number in its name ("1_Ch 02 Complete" → chapter 2)
# Without --text the only text in output/pdf/ is used; if there are several, they are listed to pick from.
# First run downloads the speech model once (~180 MB, needs internet) into ~/.recite-coach/; after that
# everything runs offline on this Mac. The page opens in your browser; press Ctrl+C here to stop.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
TEXT=""; AUDIO=""; PORT=8770
while [[ $# -gt 0 ]]; do
  case $1 in
    --text) TEXT=$2; shift 2 ;;
    --audio) AUDIO=$2; shift 2 ;;
    --port) PORT=$2; shift 2 ;;
    -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
    *) echo "error: unknown option $1" >&2; exit 2 ;;
  esac
done

# Text: a .jsonl path, a folder holding one, or a name under output/pdf/.
text_in() { shopt -s nullglob; local f=("$1"/*.romanized.jsonl "$1"/romanized/*.romanized.jsonl); shopt -u nullglob
            if [[ ${#f[@]} -gt 0 ]]; then echo "${f[0]}"; fi; }
if [[ -z "$TEXT" ]]; then
  shopt -s nullglob; FOUND=("$ROOT"/output/pdf/*/romanized/*.romanized.jsonl); shopt -u nullglob
  if [[ ${#FOUND[@]} -eq 0 ]]; then
    echo "error: no converted text in output/pdf/ — run ./convert.sh first, or pass --text" >&2; exit 2
  elif [[ ${#FOUND[@]} -gt 1 ]]; then
    echo "error: several texts found; pick one with --text <name>:" >&2
    for f in "${FOUND[@]}"; do d=${f%/romanized/*}; echo "  --text \"${d##*/}\"" >&2; done
    exit 2
  fi
  TEXT=${FOUND[0]}
elif [[ ! -f "$TEXT" ]]; then
  T=""
  [[ -d "$TEXT" ]] && T=$(text_in "$TEXT")
  [[ -z "$T" && -d "$ROOT/output/pdf/$TEXT" ]] && T=$(text_in "$ROOT/output/pdf/$TEXT")
  [[ -n "$T" ]] || { echo "error: no .romanized.jsonl for --text $TEXT (looked in output/pdf/$TEXT/romanized/)" >&2; exit 2; }
  TEXT=$T
fi

# Audio: a folder, or a name under output/mp3/; default: all of output/mp3/ (one folder per chapter).
if [[ -z "$AUDIO" ]]; then
  [[ -d "$ROOT/output/mp3" ]] && AUDIO="$ROOT/output/mp3"
elif [[ ! -d "$AUDIO" && -d "$ROOT/output/mp3/$AUDIO" ]]; then
  AUDIO="$ROOT/output/mp3/$AUDIO"
fi
AUDIO_OPT=()
if [[ -n "$AUDIO" && -d "$AUDIO" ]]; then
  AUDIO_OPT=(--audio "$AUDIO")
else
  echo "note: no instructor audio${AUDIO:+ at $AUDIO} — slokas will have no instructor audio (run ./split-audio.sh)"
fi
echo "text:  $TEXT"
echo "audio: ${AUDIO:-none}"

export UV_NO_EDITABLE=1
unset VIRTUAL_ENV
P=(--project "$ROOT/recitation-coach")
uv run -q "${P[@]}" recite-setup          # downloads the model only if missing or corrupted
exec uv run -q "${P[@]}" recite-serve --text "$TEXT" ${AUDIO_OPT[@]+"${AUDIO_OPT[@]}"} --port "$PORT"
