"""Offline review page for checking every cut by ear (FR-AS-14, 15)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

TEXT_UNREADABLE = "text_unreadable"


def load_sloka_text(path: Path) -> dict[int, dict[str, list[str]]]:
    """Verse n → {"speaker": [...], "dev": [...], "iast": [...]} from a feature-002 .romanized.jsonl file.

    A speaker unit is attached to the verse that follows it.
    """
    text: dict[int, dict[str, list[str]]] = {}
    speaker: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        unit = rec["extracted"]
        if unit["unit_type"] == "speaker":
            speaker = list(rec["romanized_lines"]["iast"])
            continue
        ref = (unit.get("verse_ref") or {}).get("normalized")
        if unit["unit_type"] != "verse" or not ref or not str(ref).isdigit():
            speaker = []
            continue
        text[int(ref)] = {
            "speaker": speaker,
            "dev": list(unit["lines"]),
            "iast": list(rec["romanized_lines"]["iast"]),
        }
        speaker = []
    return text


def render(source: str, parts: list[dict[str, Any]], text: dict[int, dict[str, list[str]]]) -> str:
    data = {
        "source": source,
        "parts": [{**p, "text": text.get(p["number"]) if p["kind"] == "sloka" else None} for p in parts],
    }
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True).replace("</", "<\\/")
    title = f"Review: {source}"
    return _TEMPLATE.replace("__TITLE__", _esc(title)).replace("__DATA__", payload)


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root {
  --bg: #f7f6f2; --card: #ffffff; --ink: #1f1d1a; --muted: #6b665d; --line: #e3dfd6;
  --accent: #8a4b14; --ok: #2f7d32; --bad: #b3261e; --warn: #9a6700; --sel: #fff4e5;
}
@media (prefers-color-scheme: dark) {
  :root { --bg: #171614; --card: #211f1c; --ink: #ece8e1; --muted: #a39d92; --line: #36332e;
          --accent: #e0a060; --ok: #7cc47f; --bad: #f2867e; --warn: #e3b341; --sel: #2c2620; }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink);
       font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
header { position: sticky; top: 0; z-index: 2; background: var(--bg); border-bottom: 1px solid var(--line);
         padding: 12px 16px; }
h1 { font-size: 17px; margin: 0 0 6px; }
.bar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.progress { flex: 1 1 220px; min-width: 180px; }
.meter { height: 6px; background: var(--line); border-radius: 3px; overflow: hidden; margin-top: 4px; }
.meter > div { height: 100%; background: var(--ok); width: 0; transition: width .2s; }
button, select { font: inherit; color: var(--ink); background: var(--card); border: 1px solid var(--line);
                 border-radius: 6px; padding: 5px 10px; cursor: pointer; }
button:hover { border-color: var(--accent); }
button.on { background: var(--accent); color: var(--bg); border-color: var(--accent); }
label.toggle { display: inline-flex; gap: 6px; align-items: center; color: var(--muted); }
main { max-width: 980px; margin: 0 auto; padding: 12px 16px 80px; }
.help { color: var(--muted); font-size: 13px; margin: 4px 0 12px; }
kbd { border: 1px solid var(--line); border-bottom-width: 2px; border-radius: 4px; padding: 0 4px; font-size: 12px; }
.part { background: var(--card); border: 1px solid var(--line); border-left: 4px solid var(--line);
        border-radius: 8px; padding: 12px 14px; margin: 10px 0; }
.part.current { background: var(--sel); border-color: var(--accent); }
.part[data-status="ok"] { border-left-color: var(--ok); }
.part[data-status="early"], .part[data-status="late"], .part[data-status="start"], .part[data-status="other"]
  { border-left-color: var(--bad); }
.head { display: flex; flex-wrap: wrap; gap: 6px 12px; align-items: baseline; }
.name { font-weight: 600; font-size: 16px; }
.meta { color: var(--muted); font-size: 13px; font-variant-numeric: tabular-nums; }
.text { margin: 8px 0; display: grid; gap: 2px; }
.text .speaker { color: var(--muted); font-style: italic; }
.text .dev { font-size: 17px; }
.text .iast { color: var(--muted); }
audio { width: 100%; margin: 6px 0; }
.row { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.status button[data-s="ok"].on { background: var(--ok); border-color: var(--ok); }
.status button.on:not([data-s="ok"]) { background: var(--bad); border-color: var(--bad); }
input.note { flex: 1 1 200px; min-width: 0; font: inherit; color: var(--ink); background: var(--bg);
             border: 1px solid var(--line); border-radius: 6px; padding: 5px 8px; }
.hidden { display: none; }
</style>
</head>
<body>
<header>
  <h1 id="title"></h1>
  <div class="bar">
    <div class="progress"><span id="count"></span><div class="meter"><div id="meterfill"></div></div></div>
    <select id="filter" aria-label="Show">
      <option value="all">Show all</option><option value="unchecked">Unchecked</option>
      <option value="problems">Problems</option>
    </select>
    <label class="toggle"><input type="checkbox" id="autonext"> Auto-play next</label>
    <button id="export">Export findings</button>
    <button id="reset" title="Clear all marks">Reset</button>
  </div>
</header>
<main>
  <p class="help">For each file: does it start at line 1 and end after line 4? Use <b>▶ Start</b> / <b>▶ End</b> to hear
  just the first / last 5 seconds. Keys: <kbd>j</kbd>/<kbd>k</kbd> next/previous, <kbd>s</kbd> start,
  <kbd>e</kbd> end, <kbd>space</kbd> play/pause, <kbd>1</kbd> OK (and move on), <kbd>2</kbd> ends early,
  <kbd>3</kbd> ends late, <kbd>4</kbd> starts wrong, <kbd>5</kbd> other. Marks are kept in this browser.</p>
  <div id="list"></div>
</main>
<script>
const DATA = __DATA__;
const STATUSES = [["ok", "OK"], ["early", "Ends too early"], ["late", "Ends too late"],
                  ["start", "Starts wrong"], ["other", "Other"]];
const KEY = "sloka-review:" + DATA.source;
let marks = {};
try { marks = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { marks = {}; }
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(marks)); } catch (e) {} };
const fmt = s => { const m = Math.floor(s / 60), r = s - 60 * m; return m + ":" + r.toFixed(1).padStart(4, "0"); };
const el = (tag, cls, txt) => { const e = document.createElement(tag); if (cls) e.className = cls;
                                if (txt != null) e.textContent = txt; return e; };

document.getElementById("title").textContent = "Review cuts — " + DATA.source;
const list = document.getElementById("list");
const rows = [];
let current = 0, stopAt = null;

DATA.parts.forEach((p, i) => {
  const card = el("section", "part"); card.dataset.idx = i;
  const head = el("div", "head");
  head.append(el("span", "name", p.kind === "sloka" ? "Sloka " + p.number : p.kind[0].toUpperCase() + p.kind.slice(1)),
              el("span", "meta", fmt(p.start_s) + " – " + fmt(p.end_s) + " in original · "
                                 + p.duration_s.toFixed(1) + " s · " + p.file));
  card.append(head);
  if (p.text) {
    const t = el("div", "text");
    p.text.speaker.forEach(x => t.append(el("div", "speaker", x)));
    p.text.dev.forEach(x => t.append(el("div", "dev", x)));
    p.text.iast.forEach(x => t.append(el("div", "iast", x)));
    card.append(t);
  }
  const audio = el("audio"); audio.controls = true; audio.preload = "none"; audio.src = p.file;
  card.append(audio);
  const ctl = el("div", "row");
  const bStart = el("button", null, "▶ Start"), bEnd = el("button", null, "▶ End");
  bStart.onclick = () => playClip(i, "start"); bEnd.onclick = () => playClip(i, "end");
  ctl.append(bStart, bEnd);
  const st = el("div", "row status");
  STATUSES.forEach(([k, label]) => { const b = el("button", null, label); b.dataset.s = k;
                                     b.onclick = () => setMark(i, k); st.append(b); });
  const note = el("input", "note"); note.placeholder = "Note (optional)";
  note.value = (marks[p.file] || {}).note || "";
  note.oninput = () => { marks[p.file] = Object.assign(marks[p.file] || {}, { note: note.value }); save(); };
  ctl.append(st, note);
  card.append(ctl);
  card.addEventListener("click", () => select(i, false));
  audio.addEventListener("timeupdate", () => {
    if (stopAt !== null && audio === rows[current].audio && audio.currentTime >= stopAt) {
      audio.pause(); stopAt = null;
    }
  });
  audio.addEventListener("ended", () => {
    if (document.getElementById("autonext").checked && i + 1 < rows.length) {
      select(i + 1, true); rows[i + 1].audio.play();
    }
  });
  list.append(card);
  rows.push({ p, card, audio, note });
});

function stopAll() { rows.forEach(r => r.audio.pause()); stopAt = null; }
function playClip(i, which) {
  select(i, false); stopAll();
  const a = rows[i].audio;
  const go = () => {
    if (which === "start") { a.currentTime = 0; stopAt = Math.min(5, a.duration); }
    else { a.currentTime = Math.max(0, a.duration - 5); stopAt = null; }
    a.play();
  };
  if (a.readyState >= 1 && isFinite(a.duration)) go();
  else { a.preload = "metadata"; a.addEventListener("loadedmetadata", go, { once: true }); a.load(); }
}
function setMark(i, status) {
  const f = rows[i].p.file;
  const same = (marks[f] || {}).status === status;  // clicking the active status clears it
  marks[f] = Object.assign(marks[f] || {}, { status: same ? undefined : status });
  save(); refresh();
}
function select(i, scroll) {
  current = Math.max(0, Math.min(rows.length - 1, i));
  rows.forEach((r, j) => r.card.classList.toggle("current", j === current));
  if (scroll) rows[current].card.scrollIntoView({ block: "center", behavior: "smooth" });
}
function refresh() {
  const filter = document.getElementById("filter").value;
  let done = 0, bad = 0;
  rows.forEach(r => {
    const s = (marks[r.p.file] || {}).status || "";
    r.card.dataset.status = s;
    r.card.querySelectorAll(".status button").forEach(b => b.classList.toggle("on", b.dataset.s === s));
    if (s) done++; if (s && s !== "ok") bad++;
    const show = filter === "all" || (filter === "unchecked" && !s) || (filter === "problems" && s && s !== "ok");
    r.card.classList.toggle("hidden", !show);
  });
  document.getElementById("count").textContent =
    done + " of " + rows.length + " checked · " + bad + " problem" + (bad === 1 ? "" : "s");
  document.getElementById("meterfill").style.width = (100 * done / rows.length) + "%";
}
document.getElementById("filter").onchange = refresh;
document.getElementById("reset").onclick = () => {
  if (!confirm("Clear all marks and notes?")) return;
  marks = {}; save(); rows.forEach(r => r.note.value = ""); refresh();
};
document.getElementById("export").onclick = () => {
  const out = { source: DATA.source, exported_at: new Date().toISOString(),
    items: rows.map(r => ({ file: r.p.file, kind: r.p.kind, number: r.p.number,
      status: (marks[r.p.file] || {}).status || "unchecked", note: (marks[r.p.file] || {}).note || "" })) };
  const blob = new Blob([JSON.stringify(out, null, 2)], { type: "application/json" });
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob);
  a.download = DATA.source.replace(/\.mp3$/i, "").replace(/ /g, "_") + ".review-findings.json";
  document.body.append(a); a.click(); a.remove();
};
document.addEventListener("keydown", ev => {
  if (ev.target.tagName === "INPUT" || ev.metaKey || ev.ctrlKey || ev.altKey) return;
  const k = ev.key;
  if (k === "j") select(current + 1, true);
  else if (k === "k") select(current - 1, true);
  else if (k === "s") playClip(current, "start");
  else if (k === "e") playClip(current, "end");
  else if (k === " ") {
    ev.preventDefault();
    const a = rows[current].audio;
    if (a.paused) { stopAll(); a.play(); } else a.pause();
  }
  else if ("12345".includes(k) && k.length === 1) {
    setMark(current, STATUSES[+k - 1][0]);
    if (k === "1") select(current + 1, true);
  } else return;
});
select(0, false); refresh();
</script>
</body>
</html>
"""
