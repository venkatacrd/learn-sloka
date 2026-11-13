# recite-coach (feature 004)

Practice page: pick a sloka, play the instructor, record yourself, get pronunciation feedback — offline on this Mac.
Spec: [specs/004-recitation-coach/](../specs/004-recitation-coach/).

```sh
./practice.sh                    # from the repo root: setup (first time), start, open http://127.0.0.1:8770/
./practice.sh --audio "1_Ch 02 Complete"   # only one chapter's instructor audio
```

First run downloads the speech model once (~180 MB) into `~/.recite-coach/` (pinned revision, SHA-256 checked); after
that nothing goes online. It needs the converted text in `output/pdf/<pdf>/romanized/` (`./convert-chapters.sh` or
`./convert.sh`) and the instructor's per-sloka MP3s in `output/mp3/<recording>/` (`./split-audio.sh`).
With a whole book the page has a chapter picker (‹ › also move across chapters). Each `output/mp3/` folder is matched
to its chapter by the number in its name (`1_Ch 02 Complete`, `1_CH 10 Complete`). A chapter whose recording was split
into a different number of parts than the book has slokas is marked ⚠ and the page warns that the instructor audio
may belong to another sloka; re-split that chapter (`./split-audio.sh … --expected N`) to fix it.

Command line (same pipeline, e.g. for Claude Code):

```sh
cd recitation-coach && UV_NO_EDITABLE=1 uv run recite-check "../input/recordings/take 1 - fail.mp3" --chapter 1 --sloka 1 \
    --text ../output/pdf/SrimadBhagawadGeeta_Sanskrit/romanized/srimadbhagawadgeeta-sanskrit-a57fb5ee.romanized.jsonl \
    --audio "../output/mp3/1_Ch 01 Complete" [--json] [--show-unsure]
```

How it works: the Su-śrotā Sanskrit speech model (ONNX, by Prof. Prathosh A P, IISc) writes down the Devanagari
letters it hears; they are compared with the sloka text letter by letter. Each difference becomes a finding with its
word, line, kind (vowel length, retroflex/dental, sibilant, aspiration, voicing, nasal, missing/extra letter or word,
visarga) and a plain sentence. Only confident findings are reported; a dropped visarga is always "unsure". Accepted
pronunciations (not mistakes): a held final vowel at the end of a line, *ācārya* said *ācārja*, म्/ं before य र ल व
श ष स ह.

Model licence: fine for personal/family use; ask the author before sharing (see the spec's brainstorm › Licence).

Tests: `uv run pytest` (text-level and server tests always; real-audio tests need the model, the book in
`output/pdf/SrimadBhagawadGeeta_Sanskrit/` and `output/mp3/1_Ch 01 Complete/`, and `input/recordings/`, and skip otherwise — about 90 s).
