#!/usr/bin/env bash
# Convenience chain: PDF(s) → Devanagari units → romanized IAST, with loss checks.
# Runs the two separate tools one after the other:
#
#   ./convert.sh [<pdf-or-folder>] [output-dir] [--pages 9-24] [--sloka-prefix NAME_] [-- extra extractor options]
#   --sloka-prefix NAME_ (or --sloka-files): also one file per sloka in <output>/romanized/slokas/
#   --sloka-no-source: sloka files hold only the IAST lines
#
# Input: PDFs live in input/pdf/. A bare file name is looked up there; no input = every PDF in input/pdf/.
# Output, per PDF (both subfolders are emptied before the run):
#   output/pdf/<pdf name>/extracted/   from ./extract-pdf.sh   (feature 001)
#   output/pdf/<pdf name>/romanized/   from ./convert-text.sh  (feature 002)
#   With --pages the folder is output/pdf/<pdf name>_pages-9-24/. An output folder given replaces output/pdf/<…>/.
# Exit code is non-zero if either step failed or lost anything.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
POS=(); EXTRA=(); PAGES=""; SLOKA_OPT=()
while [[ $# -gt 0 ]]; do
  case $1 in
    --pages) [[ $# -ge 2 ]] || { echo "error: --pages needs a value, e.g. --pages 9-24" >&2; exit 2; }
             PAGES=$2; shift 2 ;;
    --pages=*) PAGES=${1#--pages=}; shift ;;
    --sloka-files) SLOKA_OPT+=(--sloka-files); shift ;;
    --sloka-no-source) SLOKA_OPT+=(--sloka-no-source); shift ;;
    --sloka-prefix) [[ $# -ge 2 ]] || { echo "error: --sloka-prefix needs a value, e.g. --sloka-prefix ch01_sloka_" >&2; exit 2; }
                    SLOKA_OPT+=(--sloka-prefix "$2"); shift 2 ;;
    --sloka-prefix=*) SLOKA_OPT+=(--sloka-prefix "${1#--sloka-prefix=}"); shift ;;
    --) shift; EXTRA+=("$@"); break ;;
    *) POS+=("$1"); shift ;;
  esac
done
PAGE_OPT=(); [[ -n "$PAGES" ]] && PAGE_OPT=(--pages "$PAGES")
INBOX="$ROOT/input/pdf"
if [[ ${#POS[@]} -lt 1 ]]; then
  [[ -d "$INBOX" ]] || { sed -n '2,14p' "$0"; exit 2; }
  POS=("$INBOX")
fi
IN="${POS[0]}"
[[ ! -e "$IN" && -e "$INBOX/$IN" ]] && IN="$INBOX/$IN"
[[ -e "$IN" ]] || { echo "error: ${POS[0]} not found (PDFs go in input/pdf/)" >&2; exit 2; }

# A folder and no output folder: one run per PDF, each into its own output/pdf/<name>/ folder.
if [[ -d "$IN" && ${#POS[@]} -lt 2 ]]; then
  shopt -s nullglob; PDFS=("$IN"/*.[pP][dD][fF]); shopt -u nullglob
  [[ ${#PDFS[@]} -gt 0 ]] || { echo "error: no PDF in $IN" >&2; exit 2; }
  ALL=0
  for f in "${PDFS[@]}"; do
    echo "==== $(basename "$f")"
    "$0" "$f" ${PAGE_OPT[@]+"${PAGE_OPT[@]}"} ${SLOKA_OPT[@]+"${SLOKA_OPT[@]}"} -- ${EXTRA[@]+"${EXTRA[@]}"} || ALL=1
  done
  exit $ALL
fi
NAME="$(basename "$IN")"; NAME="${NAME%.*}"; [[ -n "$PAGES" ]] && NAME+="_pages-${PAGES//,/_}"
OUT="${POS[1]:-$ROOT/output/pdf/$NAME}"

echo "== 1/2 PDF reader"
"$ROOT/extract-pdf.sh" "$IN" "$OUT/extracted" ${PAGE_OPT[@]+"${PAGE_OPT[@]}"} -- ${EXTRA[@]+"${EXTRA[@]}"} || EX=$?
echo "== 2/2 text converter"
"$ROOT/convert-text.sh" "$OUT/extracted" "$OUT/romanized" ${SLOKA_OPT[@]+"${SLOKA_OPT[@]}"} || TR=$?
STATUS=$(( ${EX:-0} || ${TR:-0} ))
[[ $STATUS -ne 0 ]] && echo "FAILED (extract=${EX:-0} romanize=${TR:-0})"
exit $STATUS
