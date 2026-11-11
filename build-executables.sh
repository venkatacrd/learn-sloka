#!/usr/bin/env bash
# Build the three tools as standalone, single-file executables (no Python or uv needed to run them).
#
#   ./build-executables.sh            # all three
#   ./build-executables.sh sloka-split sanskrit-romanize   # only some
#
# Output: dist/sanskrit-extract (PDF reader), dist/sanskrit-romanize (text converter), dist/sloka-split (MP3 splitter)
# Built with PyInstaller inside each project's own environment, so each binary holds only its own dependencies.
# The binaries run on the same OS/CPU they were built on (here: macOS). OCR in sanskrit-extract still needs
# Tesseract installed (brew install tesseract tesseract-lang); everything else is inside the binary.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
export UV_NO_EDITABLE=1
unset VIRTUAL_ENV
export PYTHONWARNINGS="ignore::SyntaxWarning"   # aksharamukha's old regexes are noisy at build time
TOOLS=("$@")
[[ ${#TOOLS[@]} -eq 0 ]] && TOOLS=(sanskrit-extract sanskrit-romanize sloka-split)

build() {  # build <name> <project dir> <module> [uv extras / pyinstaller options...]
  local name=$1 project=$2 module=$3; shift 3
  local extras=() opts=()
  for a in "$@"; do [[ $a == --extra=* ]] && extras+=(--extra "${a#--extra=}") || opts+=("$a"); done
  echo "== building dist/$name"
  (cd "$ROOT/$project" && uv run -q ${extras[@]+"${extras[@]}"} --with "pyinstaller>=6.10" pyinstaller \
    --noconfirm --clean --onefile --log-level WARN --name "$name" \
    --distpath "$ROOT/dist" --workpath "$ROOT/.build/$name" --specpath "$ROOT/.build" \
    ${opts[@]+"${opts[@]}"} "$ROOT/packaging/${module}_main.py")
  "$ROOT/dist/$name" --version >/dev/null && echo "   ok: $("$ROOT/dist/$name" --version)"
}

for t in "${TOOLS[@]}"; do
  case $t in
    sanskrit-extract)
      build sanskrit-extract pdf-extractor sanskrit_extract --extra=ocr \
        --collect-all sanskrit_extract --collect-all pymupdf ;;
    sanskrit-romanize)
      build sanskrit-romanize transliterator sanskrit_romanize --extra=crosscheck \
        --collect-all sanskrit_romanize --collect-all indic_transliteration --collect-all aksharamukha \
        --collect-data jsonschema_specifications \
        --add-data "$ROOT/specs/contracts:sanskrit_romanize/contracts" ;;
    sloka-split)
      build sloka-split audio-splitter sloka_split \
        --hidden-import _cffi_backend ;;   # miniaudio's C binding needs it; PyInstaller misses it
    *) echo "unknown tool: $t (sanskrit-extract | sanskrit-romanize | sloka-split)" >&2; exit 2 ;;
  esac
done
ls -lh "$ROOT/dist"
