# 004 – Recitation Coach: Tasks

Increment 1 (practice page). Tests first; each test name carries its AC ID. **Status 2026-11-11: T01–T09 done.**

| ID | Task | Satisfies | Tests to write first | Depends |
|----|------|-----------|----------------------|---------|
| RC-T01 | Scaffold `recitation-coach/` (uv, ruff, mypy strict), CLI `--version` | constitution 9, 11 | `test_cli_version` | – |
| RC-T02 | `library.py`: verses + speaker placement + audio mapping | FR-RC-01 | AC-RC-01 | T01 |
| RC-T03 | `normalize.py`: comparison form with char→word map | FR-RC-05 | AC-RC-03 | T01 |
| RC-T04 | `compare.py` + `feedback.py`: regions, kinds, confidence, score, sentences | FR-RC-06, 07, 08, 10 | AC-RC-04, AC-RC-11 | T03 |
| RC-T05 | `model.py`: pinned download + checksum, transcribe with times/probs | FR-RC-04, 13 | AC-RC-12 | T01 |
| RC-T06 | `cli.py` `recite-check`, `recite-setup` | FR-RC-12, 13 | AC-RC-09 | T02–T05 |
| RC-T07 | Real-audio acceptance: learner takes, teacher false-alarm rate | FR-RC-04–08 | AC-RC-05, AC-RC-06 | T06 |
| RC-T08 | `server.py` + `static/index.html`: sloka view, instructor playback, record → WAV, submit, feedback, word playback | FR-RC-03, 10 | AC-RC-08, AC-RC-10 | T06 |
| RC-T09 | `practice.sh`, `.gitignore`, README, CLAUDE.md | FR-RC-13 | manual run | T08 |
| RC-T10 | Repository layout: `practice.sh` defaults and short names for `output/pdf/`, `output/mp3/`; test paths | FR-RC-01, 13 | manual run | T09 |
| RC-T11 | Whole book: chapters in library/coach/server/CLI, chapter picker and audio-count warning on the page, `practice.sh` audio root default | FR-RC-14 | AC-RC-13, AC-RC-14 | T10 |
| RC-T12 | Telugu line per word on the page, script switches (default all, remembered) | FR-RC-03 | AC-RC-15 | T11 |

Increment 2 (later): profiles (FR-RC-02), history (FR-RC-11), accepted-variants page action (FR-RC-09).
