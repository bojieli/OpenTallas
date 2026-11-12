#!/usr/bin/env python3
"""COORD state snapshot for Codex takeover (OWNER 11-12).

Runs from cron on the hub (intel2) every 15 min. No LLM is involved: it only reads
coord files and ot-run status, writes lanes/handoff/COORD-SNAPSHOT.md and commits it
through bin/coord-commit.sh. It never deletes, kills or edits anything else.

Usage: coord_snapshot.py [--dry]   (--dry prints the snapshot, writes and commits nothing)
"""
import os
import re
import subprocess as S
import sys
import time
from pathlib import Path

COORD = Path("/home/ubuntu/coord")
QUEUE = COORD / "lanes/COORD-REVIEW-QUEUE.md"
HANDOFF_DIR = COORD / "lanes/handoff"
OUT = HANDOFF_DIR / "COORD-SNAPSHOT.md"
AUTOPILOT_LOG = COORD / "autopilot/log.txt"
OTRUN = "/home/ubuntu/.local/bin/ot-run"

POST_RE = re.compile(r"^- (\d{4}-\d{2}-\d{2}) (\S+) PST (\w[\w-]*) +\[([^\]]*)\]")
SHA_RE = re.compile(r"@([0-9a-f]{7,40})")
RECENT_POSTS = 60       # last N queue posts, verbatim but cut
OPEN_SCAN_POSTS = 600   # how far back to look for open READY/ASK
CUT = 420


def run(cmd, timeout=60):
    try:
        p = S.run(cmd, capture_output=True, text=True, timeout=timeout, stdin=S.DEVNULL)
        return p.stdout
    except Exception as e:  # snapshot must never fail on one source
        return f"(unavailable: {e})"


def tail_lines(path, n_bytes=6_000_000):
    """Last part of a big append-only file, as lines (the queue is ~27 MB)."""
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - n_bytes))
            data = f.read().decode("utf-8", "replace")
        lines = data.splitlines()
        return lines[1:] if size > n_bytes else lines
    except OSError as e:
        return [f"(unavailable: {e})"]


def posts(lines):
    out = []
    for ln in lines:
        m = POST_RE.match(ln)
        if m:
            date, hhmm, kind, head = m.groups()
            lane = head.split("->")[0].strip().split()[0] if head.strip() else "?"
            out.append({"date": date, "hhmm": hhmm, "kind": kind, "lane": lane, "line": ln})
    return out


def open_items(ps):
    """READY/ASK posts with no later [COORD ...] post naming their sha (READY) or their lane (ASK).
    Heuristic: a later COORD post may answer without naming them; it is listed for Codex to check."""
    scan = ps[-OPEN_SCAN_POSTS:]
    today = scan[-1]["date"] if scan else ""
    res = []
    for i, p in enumerate(scan):
        if p["kind"] not in ("READY", "ASK") or p["lane"] == "COORD" or p["date"] != today:
            continue
        shas = [s[:8] for s in SHA_RE.findall(p["line"])]
        # an answer is a later COORD ruling or a merge-lane MERGED/RESULT naming the sha
        later = [q["line"] for q in scan[i + 1:]
                 if q["lane"] == "COORD" or q["lane"].startswith("ROOT-MERGE")]
        if shas:
            answered = any(any(s in l for s in shas) for l in later)
        else:
            answered = any(p["lane"] in l for l in later)
        if not answered:
            res.append(p)
    return res


def lane_last_post(ps):
    last = {}
    for p in ps:
        last[p["lane"]] = f'{p["date"]} {p["hhmm"]} {p["kind"]}'
    return last


def main():
    dry = "--dry" in sys.argv
    now = time.strftime("%Y-%m-%d %H:%M %Z")
    lines = tail_lines(QUEUE)
    ps = posts(lines)
    last = lane_last_post(ps)
    opn = open_items(ps)

    o = []
    o.append(f"# COORD snapshot {now}")
    o.append("")
    o.append("Generated every 15 min by ~/coord/bin/coord_snapshot.py (cron on intel2, no LLM). "
             "It is the freshest COORD state if Claude stops on a limit. Read it right after "
             "~/coord/CODEX-HANDOFF.md (the hand-written method and lane table) and "
             "~/coord/lanes/handoff/<LANE>.md (each lane's own state). Facts only; the queue is the source.")
    o.append("")

    o.append("## main and the merge lane")
    main_sha = run(["git", "-C", str(COORD), "ls-remote", "origin", "refs/heads/main"], 30).split()
    o.append(f"- origin/main: {main_sha[0][:12] if main_sha else '?'}")
    merged = [p["line"][:CUT] for p in ps if p["kind"] == "MERGED"][-3:]
    for m in merged:
        o.append(f"- {m[2:]}")
    o.append("")

    o.append(f"## READY/ASK with no later COORD post naming them ({len(opn)}, heuristic: check each)")
    for p in opn[-40:]:
        o.append(f"- {p['line'][2:CUT]}")
    o.append("")

    o.append("## Lane handoff files (age) and last queue post")
    try:
        files = sorted(HANDOFF_DIR.glob("*.md"))
    except OSError:
        files = []
    for f in files:
        if f.name == OUT.name:
            continue
        lane = f.stem
        age_min = int((time.time() - f.stat().st_mtime) / 60)
        o.append(f"- {lane}: handoff {age_min} min old; last post {last.get(lane, 'none in recent queue')}")
    o.append("")

    o.append("## ot-run status")
    st = run([OTRUN, "--status"], 90)
    for part in st.replace("|", "\n").splitlines():
        if part.strip():
            o.append(f"    {part.strip()[:160]}")
    o.append("")

    o.append("## KIT-WAVE (autopilot log, last 6)")
    kw = [l for l in tail_lines(AUTOPILOT_LOG, 3_000_000) if "KIT-WAVE" in l][-6:]
    for l in kw:
        o.append(f"    {l[:200]}")
    o.append("")

    o.append(f"## Last {RECENT_POSTS} queue posts (cut to {CUT} chars; full text in the queue)")
    for p in ps[-RECENT_POSTS:]:
        o.append(f"- {p['line'][2:CUT]}")
    o.append("")

    text = "\n".join(o) + "\n"
    if dry:
        sys.stdout.write(text)
        return 0
    tmp = OUT.with_suffix(".md.tmp")
    tmp.write_text(text)
    os.replace(tmp, OUT)
    r = S.run(["bash", str(COORD / "bin/coord-commit.sh"), f"coord snapshot {now}",
               str(OUT.relative_to(COORD))], capture_output=True, text=True, timeout=240)
    print(f"{now} commit rc={r.returncode} {r.stderr.strip()[:200]}")
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
