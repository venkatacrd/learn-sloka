#!/usr/bin/env bash
# Text converter (feature 002): extracted Devanagari JSONL → IAST and Telugu script, with a loss check.
#
#   ./convert-text.sh <jsonl-or-folder> [output-dir] [--pages 9-24] [--sloka-prefix NAME_] [-- extra options]
#   ./convert-text.sh output/pdf/<pdf name>/extracted      → output/pdf/<pdf name>/romanized/
#
# --pages: convert only units from these PDF pages (5, 1-10, 1,3-4 or 10-).
# --sloka-prefix NAME_: also write one file per sloka, <output>/slokas/NAME_01.txt, NAME_02.txt, …
#   (number = verse number; Devanagari lines, blank line, IAST lines). --sloka-files does the same with "sloka_".
# Sloka files: Devanagari, blank line, Telugu, blank line, IAST. --sloka-no-source leaves out the Devanagari.
# Input: output of ./extract-pdf.sh (output/pdf/<pdf name>/extracted/).
# Output: the folder romanized/ next to an …/extracted input folder, otherwise output/pdf/<input name>/romanized/,
#   unless an output folder is given. The output folder is emptied before every run.
# Output per document: <doc>.romanized.jsonl / .romanized.report.json / .romanized.txt (readable)
# Exit code is non-zero if an input failed or a unit's IAST does not convert back to the same Devanagari.
# Every unit is also romanized by a second engine (aksharamukha); disagreements are listed for review.
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
if [[ ${#POS[@]} -lt 1 ]]; then sed -n '2,16p' "$0"; exit 2; fi
[[ -e "${POS[0]}" ]] || { echo "error: ${POS[0]} not found" >&2; exit 2; }
IN="$(cd "$(dirname "${POS[0]}")" && pwd)/$(basename "${POS[0]}")"
if [[ -d "$IN" && "$(basename "$IN")" == extracted ]]; then
  DEFAULT_OUT="$(dirname "$IN")/romanized"
else
  NAME="$(basename "$IN")"; NAME="${NAME%.jsonl}"
  DEFAULT_OUT="$ROOT/output/pdf/$NAME/romanized"
fi
OUT="${POS[1]:-$DEFAULT_OUT}"
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"

# Empty the output folder, but never one that holds the input (or is /, or $HOME).
IN_DIR="$([[ -d "$IN" ]] && echo "$IN" || dirname "$IN")"
case "$IN_DIR/" in "$OUT"/*) echo "error: refusing to clean $OUT: it contains the input" >&2; exit 2;; esac
[[ "$OUT" == "/" || "$OUT" == "$HOME" ]] && { echo "error: refusing to clean $OUT" >&2; exit 2; }
find "$OUT" -mindepth 1 -delete

export UV_NO_EDITABLE=1
unset VIRTUAL_ENV

echo "== romanize: $IN${PAGES:+ (pages $PAGES)} -> $OUT"
uv run -q --project "$ROOT/transliterator" --extra crosscheck sanskrit-romanize "$IN" -o "$OUT" \
  --schemes iast,telugu --strict --cross-check ${PAGE_OPT[@]+"${PAGE_OPT[@]}"} ${SLOKA_OPT[@]+"${SLOKA_OPT[@]}"} \
  ${EXTRA[@]+"${EXTRA[@]}"} || TR=$?

python3 - "$OUT" <<'PY' || CHECK=$?
import json, pathlib, sys
out = pathlib.Path(sys.argv[1]); bad = 0
reports = sorted(out.glob("*.romanized.report.json"))
if not reports:
    print("no romanized output (see errors above)"); bad = 1
for rr in reports:
    t = json.loads(rr.read_text())
    doc = rr.name.removesuffix(".romanized.report.json")
    print(f"{doc}: romanized {t['units_out']}/{t['units_in']} units; round-trip OK {t['roundtrip_ok']}/{t['units_out']}"
          f" → {out / (doc + '.romanized.txt')}")
    for x in t.get("source_invalid", []):
        print(f"    REVIEW {x['unit_id']}: the PDF's own text is not valid Devanagari here (kept as-is, flagged)")
    for x in t["roundtrip_failures"]:
        print(f"    LOSS {x['unit_id']}: {x['warnings'][-1]}")
    bad += t["units_out"] != t["units_in"] or bool(t["roundtrip_failures"])
    rom = out / f"{doc}.romanized.jsonl"
    cross = [json.loads(x) for x in rom.read_text(encoding="utf-8").splitlines() if "cross_check_disagreement" in x]
    print(f"  second transliteration engine: {'agrees on every unit' if not cross else f'{len(cross)} disagreement(s)'}")
    for x in cross:
        print(f"    REVIEW {x['extracted']['unit_id']}: engines differ")
print("RESULT:", "nothing lost in romanization" if not bad else f"{bad} problem(s) — see messages and reports")
sys.exit(1 if bad else 0)
PY
STATUS=$(( ${TR:-0} || ${CHECK:-0} ))
[[ $STATUS -ne 0 ]] && echo "FAILED (romanize=${TR:-0} check=${CHECK:-0})"
exit $STATUS
