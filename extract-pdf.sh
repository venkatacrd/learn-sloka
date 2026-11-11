#!/usr/bin/env bash
# PDF reader (feature 001): Sanskrit PDF(s) → Devanagari units as JSONL, with a loss check.
#
#   ./extract-pdf.sh <pdf-or-folder> [output-dir] [--pages 9-24] [-- extra options, e.g. --force-ocr]
#
# --pages: 5, 1-10, 1,3-4 or 10- (to the last page). Pages the PDF does not have are reported.
# Running headers/footers (including alternating book headers and lines outside the page's separator rules)
# and page numbers are left out; each removed line is listed in the report.
# The output folder (default: pdf-outs/ next to this script) is emptied before every run.
# Output per PDF: <doc>.jsonl (one unit per line) and <doc>.report.json
# Exit code is non-zero if a file failed, a PDF line was not accounted for, or a legacy-font code is unknown.
# When Tesseract with the Sanskrit model is installed, every unit is also read by OCR and compared
# (disagreements are listed for review; they do not fail the run).
# Next step: ./convert-text.sh <output-dir>
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
POS=(); EXTRA=(); PAGES=""
while [[ $# -gt 0 ]]; do
  case $1 in
    --pages) [[ $# -ge 2 ]] || { echo "error: --pages needs a value, e.g. --pages 9-24" >&2; exit 2; }
             PAGES=$2; shift 2 ;;
    --pages=*) PAGES=${1#--pages=}; shift ;;
    --) shift; EXTRA+=("$@"); break ;;
    *) POS+=("$1"); shift ;;
  esac
done
PAGE_OPT=(); [[ -n "$PAGES" ]] && PAGE_OPT=(--pages "$PAGES")
if [[ ${#POS[@]} -lt 1 ]]; then sed -n '2,15p' "$0"; exit 2; fi
[[ -e "${POS[0]}" ]] || { echo "error: ${POS[0]} not found" >&2; exit 2; }
IN="$(cd "$(dirname "${POS[0]}")" && pwd)/$(basename "${POS[0]}")"
OUT="${POS[1]:-$ROOT/pdf-outs}"
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"

# Empty the output folder, but never one that holds the input (or is /, or $HOME).
IN_DIR="$([[ -d "$IN" ]] && echo "$IN" || dirname "$IN")"
case "$IN_DIR/" in "$OUT"/*) echo "error: refusing to clean $OUT: it contains the input" >&2; exit 2;; esac
[[ "$OUT" == "/" || "$OUT" == "$HOME" ]] && { echo "error: refusing to clean $OUT" >&2; exit 2; }
find "$OUT" -mindepth 1 -delete

export UV_NO_EDITABLE=1   # see pdf-extractor/README.md, Troubleshooting
unset VIRTUAL_ENV

VERIFY=()
if command -v tesseract >/dev/null && tesseract --list-langs 2>/dev/null | grep -qx san; then
  VERIFY=(--verify-ocr)
else
  echo "note: Tesseract with Sanskrit model not found; OCR cross-check skipped (brew install tesseract tesseract-lang)"
fi

echo "== extract: $IN${PAGES:+ (pages $PAGES)} -> $OUT"
uv run -q --project "$ROOT/pdf-extractor" --extra ocr sanskrit-extract "$IN" -o "$OUT" ${PAGE_OPT[@]+"${PAGE_OPT[@]}"} \
  ${VERIFY[@]+"${VERIFY[@]}"} ${EXTRA[@]+"${EXTRA[@]}"} \
  || EX=$?

python3 - "$OUT" <<'PY' || CHECK=$?
import json, pathlib, sys
out = pathlib.Path(sys.argv[1]); bad = 0
reports = sorted(out.glob("*.report.json"))
if not reports:
    print("no extractor output (see errors above)"); bad = 1
for rep in reports:
    r = json.loads(rep.read_text()); c = r["coverage"]
    print(f"{r['file_name']}: {c['lines_read']} lines read = {c['lines_in_units']} in units + "
          f"{c['lines_removed']} removed (listed in report); unaccounted {c['unaccounted']}; "
          f"unknown font codes {len(r['unknown_legacy_codes'])}; units for review {len(r['flagged'])}")
    bad += c["unaccounted"] != 0 or bool(r["unknown_legacy_codes"])
    v = r.get("verification")
    if v:
        print(f"  OCR cross-check: {v['units_checked']} units, mean difference {v['mean_cer']:.0%}, "
              f"{v['units_disagreeing']} clear disagreement(s) (> {v['cer_threshold']:.0%})")
        if v.get("units_ocr_empty"):
            print(f"    {len(v['units_ocr_empty'])} unit(s) OCR could not read (not checked)")
        for d in v["disagreements"]:
            print(f"    REVIEW {d['unit_id']}: {d['cer']:.0%} different from OCR")
print("RESULT:", "nothing lost in extraction" if not bad else f"{bad} problem(s) — see messages and reports")
sys.exit(1 if bad else 0)
PY
STATUS=$(( ${EX:-0} || ${CHECK:-0} ))
[[ $STATUS -ne 0 ]] && echo "FAILED (extract=${EX:-0} check=${CHECK:-0})"
exit $STATUS
