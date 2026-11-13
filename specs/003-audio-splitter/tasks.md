# 003 – Audio Splitter: Tasks

| ID | Task | Satisfies | Tests to write first | Depends |
|----|------|-----------|----------------------|---------|
| AS-T01 | Scaffold `audio-splitter/`, CLI `--version` | constitution 9, 11 | `test_cli_version` | – |
| AS-T02 | `tests/synth.py`: synthetic chant generator (PCM + MP3 via lameenc) | – | – | T01 |
| AS-T03 | `mp3frames.py` | FR-AS-06, NFR-AS-01 | AC-AS-05 | T02 |
| AS-T04 | `analysis.py` segments + tail pitch + cadence threshold | FR-AS-02, 03 | AC-AS-03 | T02 |
| AS-T05 | `analysis.py` sloka grouping + cut times | FR-AS-04, 05 | AC-AS-01, 02, 04 | T04 |
| AS-T06 | `splitter.py` write parts, tags, names, reports, coverage check | FR-AS-01, 07..10, NFR-AS-01, 02 | AC-AS-05..08 | T03, T05 |
| AS-T07 | Clean with safety checks | FR-AS-11 | AC-AS-09 | T06 |
| AS-T08 | `cli.py` full options, exit codes | FR-AS-12 | via CLI in AC-AS-08, 09 | T07 |
| AS-T09 | `split-audio.sh`, e2e on the reference file | FR-AS-13, NFR-AS-04 | AC-AS-10 | T08 |
| AS-T10 | README (package + root) | – | – | T09 |
| AS-T11 | Fix: half-verse may end on the line after the cadence (user report: cut at end of line 3); auto-detect from pauses, `--half-verse-end` override, breath-split lines | FR-AS-04, 12 | AC-AS-11, 12, 13 | T05 |
| AS-T12 | Review page + `--text` | FR-AS-14, 15 | AC-AS-14 | T11 |
| AS-T13 | Repository layout: `split-audio.sh` reads `input/mp3/`, writes `output/mp3/<stem>/` | FR-AS-13 | manual run | T09 |
| AS-T14 | `--name` for output file names (e.g. `CH11_sloka_01.mp3`) | FR-AS-08, 12 | AC-AS-15 | T09 |
