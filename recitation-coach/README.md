# recite-coach (feature 004)

Practice page: pick a sloka, play the instructor, record yourself, get pronunciation feedback — offline on this Mac.
Spec: [specs/004-recitation-coach/](../specs/004-recitation-coach/).

```sh
./practice.sh                    # from the repo root: setup (first time), start, open http://127.0.0.1:8770/
```

First run downloads the speech model once (~180 MB) into `~/.recite-coach/` (pinned revision, SHA-256 checked); after
that nothing goes online. It needs `text-outs/<doc>.romanized.jsonl` (`./convert-text.sh`) and the instructor's
per-sloka MP3s in `audio-outs/` (`./split-audio.sh`).

Command line (same pipeline, e.g. for Claude Code):

```sh
cd recitation-coach && UV_NO_EDITABLE=1 uv run recite-check "../audio-input-test/take 1 - fail.mp3" --sloka 1 \
    --text ../text-outs/01-chapter-sanskrit-438e578c.romanized.jsonl --audio ../audio-outs [--json] [--show-unsure]
```

How it works: the Su-śrotā Sanskrit speech model (ONNX, by Prof. Prathosh A P, IISc) writes down the Devanagari
letters it hears; they are compared with the sloka text letter by letter. Each difference becomes a finding with its
word, line, kind (vowel length, retroflex/dental, sibilant, aspiration, voicing, nasal, missing/extra letter or word,
visarga) and a plain sentence. Only confident findings are reported; a dropped visarga is always "unsure". Accepted
pronunciations (not mistakes): a held final vowel at the end of a line, *ācārya* said *ācārja*, म्/ं before य र ल व
श ष स ह.

Model licence: fine for personal/family use; ask the author before sharing (see the spec's brainstorm › Licence).

Tests: `uv run pytest` (text-level and server tests always; real-audio tests need the model, `text-outs/`,
`audio-outs/` and `audio-input-test/`, and skip otherwise — about 90 s).
