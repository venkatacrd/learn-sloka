#!/usr/bin/env bash
# Whole book → one text file per sloka (Devanagari, Telugu, IAST), named by chapter and sloka number (FR-TR-18, 19).
#
#   ./convert-chapters.sh [pdf] [--chapters 18] [--no-source]
#   ./convert-chapters.sh SrimadBhagawadGeeta_Sanskrit.pdf
#
# pdf: a file in input/pdf/ (bare name) or any path; default: the only PDF in input/pdf/.
# --chapters N   how many chapters to take, in order (default 18; parts after them, e.g. Gita Mahatmya, are skipped)
# --no-source    leave the Devanagari out of the sloka files (default: Devanagari, Telugu and IAST)
#
# Steps: ./convert.sh on the whole PDF → chapters found where the verse number restarts → ./convert-text.sh per
# chapter with its page range and --sloka-prefix CHnn_sloka_.
# Output in output/pdf/<pdf name>/:
#   extracted/, romanized/          the whole book (from ./convert.sh)
#   chapters/CH01/ … CH18/          each chapter's converted text + slokas/
#   slokas/                         all sloka files together: CH01_sloka_01.txt … CH18_sloka_78.txt
# Exit code is non-zero if a step failed or lost anything.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
INBOX="$ROOT/input/pdf"
PDF=""; CHAPTERS=18; SOURCE_OPT=()
while [[ $# -gt 0 ]]; do
  case $1 in
    --chapters) [[ $# -ge 2 ]] || { echo "error: --chapters needs a number" >&2; exit 2; }
                CHAPTERS=$2; shift 2 ;;
    --no-source) SOURCE_OPT=(--sloka-no-source); shift ;;
    --with-source) shift ;;  # the default now; kept so older commands still work
    -h|--help) sed -n '2,17p' "$0"; exit 0 ;;
    -*) echo "error: unknown option $1" >&2; exit 2 ;;
    *) PDF=$1; shift ;;
  esac
done
[[ "$CHAPTERS" =~ ^[1-9][0-9]*$ ]] || { echo "error: --chapters must be a positive number" >&2; exit 2; }
if [[ -z "$PDF" ]]; then
  shopt -s nullglob; FOUND=("$INBOX"/*.[pP][dD][fF]); shopt -u nullglob
  [[ ${#FOUND[@]} -eq 1 ]] || { echo "error: name the PDF (input/pdf/ holds ${#FOUND[@]})" >&2; exit 2; }
  PDF=${FOUND[0]}
fi
[[ ! -e "$PDF" && -e "$INBOX/$PDF" ]] && PDF="$INBOX/$PDF"
[[ -f "$PDF" ]] || { echo "error: $PDF not found (PDFs go in input/pdf/)" >&2; exit 2; }
NAME="$(basename "$PDF")"; NAME="${NAME%.*}"
BOOK="$ROOT/output/pdf/$NAME"

echo "==== 1/3 whole book: $(basename "$PDF")"
"$ROOT/convert.sh" "$PDF" > "$BOOK.log" 2>&1 || { tail -20 "$BOOK.log"; echo "FAILED: see $BOOK.log"; exit 1; }
grep -E "^RESULT" "$BOOK.log"
rm -f "$BOOK.log"

echo "==== 2/3 chapters"
shopt -s nullglob; JSONL=("$BOOK"/romanized/*.romanized.jsonl); shopt -u nullglob
[[ ${#JSONL[@]} -eq 1 ]] || { echo "error: expected one .romanized.jsonl in $BOOK/romanized" >&2; exit 2; }
# One line per chapter: "<first page> <last page> <verses>"
RANGES=$(python3 - "${JSONL[0]}" "$CHAPTERS" <<'PY'
import json, re, sys
path, wanted = sys.argv[1], int(sys.argv[2])
parts, last = [], 0
for line in open(path, encoding="utf-8"):
    u = json.loads(line)["extracted"]
    ref = (u.get("verse_ref") or {}).get("normalized", "")
    if u["unit_type"] != "verse" or not re.fullmatch(r"\d+", ref):
        continue
    n = int(ref)
    if n < last or not parts:
        parts.append({"first": u["source"]["page_start"], "last": 0, "verses": 0})
    parts[-1]["last"] = max(parts[-1]["last"], u["source"]["page_end"])
    parts[-1]["verses"] += 1
    last = n
if len(parts) < wanted:
    sys.exit(f"error: found {len(parts)} chapters, --chapters asks for {wanted}")
for i in range(wanted):
    end = parts[i + 1]["first"] - 1 if i + 1 < len(parts) else parts[i]["last"]
    if end < parts[i]["last"]:
        sys.exit(f"error: chapters {i + 1} and {i + 2} share page {parts[i + 1]['first']}; cannot split by page")
    print(parts[i]["first"], end, parts[i]["verses"])
PY
) || exit 2

echo "==== 3/3 sloka files"
rm -rf "$BOOK/chapters" "$BOOK/slokas"
mkdir -p "$BOOK/chapters" "$BOOK/slokas"
printf "%-6s %-9s %s\n" chapter pages slokas
FAIL=0; CH=0; TOTAL=0
while read -r FROM TO VERSES; do
  CH=$((CH + 1)); ID=$(printf "CH%02d" "$CH"); OUT="$BOOK/chapters/$ID"
  if "$ROOT/convert-text.sh" "$BOOK/extracted" "$OUT" --pages "$FROM-$TO" --sloka-prefix "${ID}_sloka_" \
       ${SOURCE_OPT[@]+"${SOURCE_OPT[@]}"} > "$OUT.log" 2>&1; then
    N=$(find "$OUT/slokas" -name '*.txt' | wc -l | tr -d ' ')
    cp "$OUT"/slokas/*.txt "$BOOK/slokas/"
    TOTAL=$((TOTAL + N)); rm -f "$OUT.log"
    NOTE=""; [[ "$N" -eq "$VERSES" ]] || { NOTE="  (book has $VERSES verses — check)"; FAIL=1; }
    printf "%-6s %-9s %s%s\n" "$ID" "$FROM-$TO" "$N" "$NOTE"
  else
    printf "%-6s %-9s FAILED, see %s\n" "$ID" "$FROM-$TO" "$OUT.log"; FAIL=1
  fi
done <<< "$RANGES"
echo "RESULT: $TOTAL sloka files in $BOOK/slokas"
exit $FAIL
