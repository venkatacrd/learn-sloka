#!/usr/bin/env bash
# Convenience chain: PDF(s) → Devanagari units → romanized IAST, with loss checks.
# Runs the two separate tools one after the other:
#
#   ./convert.sh <pdf-or-folder> [output-dir] [--pages 9-24] [--sloka-prefix NAME_] [-- extra extractor options]
#   --sloka-prefix NAME_ (or --sloka-files): also one file per sloka in <output>/romanized/slokas/
#   --sloka-no-source: sloka files hold only the IAST lines
#
# Output (both subfolders are emptied before the run):
#   <output>/extracted/   from ./extract-pdf.sh   (feature 001)
#   <output>/romanized/   from ./convert-text.sh  (feature 002)
# Exit code is non-zero if either step failed or lost anything. Default output: output/
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
if [[ ${#POS[@]} -lt 1 ]]; then sed -n '2,11p' "$0"; exit 2; fi
IN="${POS[0]}"
OUT="${POS[1]:-$ROOT/output}"

echo "== 1/2 PDF reader"
"$ROOT/extract-pdf.sh" "$IN" "$OUT/extracted" ${PAGE_OPT[@]+"${PAGE_OPT[@]}"} -- ${EXTRA[@]+"${EXTRA[@]}"} || EX=$?
echo "== 2/2 text converter"
"$ROOT/convert-text.sh" "$OUT/extracted" "$OUT/romanized" ${SLOKA_OPT[@]+"${SLOKA_OPT[@]}"} || TR=$?
STATUS=$(( ${EX:-0} || ${TR:-0} ))
[[ $STATUS -ne 0 ]] && echo "FAILED (extract=${EX:-0} romanize=${TR:-0})"
exit $STATUS
