#!/usr/bin/env python3
"""count_hourly.py -- refresh the release count and append lanes/SIGN-RATE.tsv each hour with no agent (FLOW-29, owner 11-04).

Why: in the limit 11-04 01:30-03:10 nothing rescanned, so SIGN-RATE has a gap from 00:36 to 03:30 and the first sign-off
back counted hours late.  Runs on the coord host, where the cache and the counter live, at :05, nice, by a timer
(systemd/count-hourly.timer).  COORD's own hourly refresh sits around :30 and the render timer at :40.

Each run: stop file -> nothing.  Cache younger than FRESH_S -> no scan (somebody just ran it), the row still goes in.
Otherwise release_tree_plan.py --force.  A scan that fails or leaves the cache unchanged appends no row and exits 1, so
systemctl and the journal show it; a gap in the file stays a true gap.  The row has the same shape as the hand rows, with
'auto' at the end; an hour already holding the same counts gets no new row.  Reads only; it credits nothing.
"""
import fcntl
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HOME = Path.home()
COORD = Path(os.environ.get("COUNT_COORD", str(HOME / "coord")))
CACHE = Path(os.environ.get("COUNT_CACHE", str(HOME / ".local/state/fleet-viz/release_tree_plan_cache.json")))
COUNTER = os.environ.get("COUNT_TOOL", str(COORD / "tools" / "release_tree_plan.py"))
COMMIT = os.environ.get("COUNT_COMMIT", str(COORD / "bin" / "coord-commit.sh"))
STATE = Path(os.environ.get("COUNT_STATE", str(HOME / ".local/state/fleet-viz")))
RATE = "lanes/SIGN-RATE.tsv"
QUEUE = "lanes/COORD-REVIEW-QUEUE.md"
FRESH_S = 30 * 60
SCAN_TIMEOUT_S = 25 * 60
DIES = (("s81", "s81"), ("s81_head", "head"), ("qwen_compute", "qc"), ("qwen_kvsys", "kv"), ("hbm", "hbm"))


def rate_row(cache, stamp):
    """'YYYY-MM-DD HH:MM total s81=37 head=4+5t qc=12 kv=20 hbm=12 auto': designs + directly signed types per die"""
    total, parts = 0, []
    for die, short in DIES:
        d = t = 0
        for e in (cache.get("plans") or {}).values():
            if e.get("die") == die:
                d += len(e.get("signed_designs") or {})
                t += len(e.get("signed_types") or {})
        total += d + t
        parts.append("%s=%d%s" % (short, d, "+%dt" % t if t else ""))
    return "%s %d %s auto" % (stamp, total, " ".join(parts))


def counts_of(row):
    return re.sub(r"\s+auto\s*$", "", row.split(" ", 2)[2]) if row.count(" ") >= 2 else ""


def same_hour_same_counts(text, row):
    hour = row[:13]
    return any(r.startswith(hour) and counts_of(r) == counts_of(row) for r in (text or "").splitlines())


def read_cache():
    return json.loads(CACHE.read_text())


def run(now=None, scan=None, commit=None):
    """-> process exit code"""
    now = now or time.time()
    if (STATE / "count_hourly.stop").exists():
        print("count_hourly: stop file, nothing done")
        return 0
    STATE.mkdir(parents=True, exist_ok=True)
    lock = open(STATE / "count_hourly.lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("count_hourly: another run holds the lock")
        return 0
    before = None
    try:
        before = float(read_cache().get("generated") or 0)
    except (OSError, ValueError) as e:
        print("count_hourly: cache unreadable before the scan: %s" % e)
    if before is None or now - before >= FRESH_S:
        rc = (scan or _scan)()
        if rc:
            print("count_hourly: scan rc %s, no row" % rc, file=sys.stderr)
            return 1
    try:
        cache = read_cache()
    except (OSError, ValueError) as e:
        print("count_hourly: cache unreadable: %s, no row" % e, file=sys.stderr)
        return 1
    if now - float(cache.get("generated") or 0) >= FRESH_S:
        print("count_hourly: cache still %d min old after the scan, no row" % ((now - float(cache.get("generated") or 0)) / 60), file=sys.stderr)
        return 1
    row = rate_row(cache, time.strftime("%Y-%m-%d %H:%M", time.localtime(now)))
    files = []
    # COUNT-ARCHIVE-2 11-10 (COORD): ADVISORY post of counted designs whose plan pin table changed (plan_pin_change.py,
    # logged by release_tree_plan.refresh), addressed to the die owner so the re-signs go in the same batch
    if post_pin_changes(now):
        files.append(QUEUE)
    p = COORD / RATE
    if same_hour_same_counts(p.read_text() if p.exists() else "", row):
        print("count_hourly: this hour already holds these counts: " + row)
    else:
        with open(p, "a") as f:
            f.write(row + "\n")
        print(row)
        files.append(RATE)
    if not files:
        return 0
    return (commit or _commit)(files)


def post_pin_changes(now):
    """append unposted plan pin-change findings to the review queue and mark them posted (a lost commit race leaves the
    lines in the tree for the next commit, like the rate row) -> True when lines were added.  Advisory: errors ignored."""
    try:
        sys.path.insert(0, str(Path(COUNTER).resolve().parent))
        import plan_pin_change as ppc
        rows, mark = ppc.unposted(CACHE.parent)
        if not rows:
            return False
        lines = ppc.queue_lines(rows, time.strftime("%Y-%m-%d %H:%M %Z", time.localtime(now)))
        with open(COORD / QUEUE, "a") as f:
            f.write("\n".join(lines) + "\n")
        mark()
        print("\n".join(lines))
        return True
    except Exception as e:   # advisory, never stops the hourly row
        print("count_hourly: plan pin change post skipped: %s" % e, file=sys.stderr)
        return False


def _scan():
    try:
        return subprocess.run([sys.executable, COUNTER, "--force"], cwd=str(COORD), timeout=SCAN_TIMEOUT_S,
                              stdout=subprocess.DEVNULL).returncode
    except subprocess.TimeoutExpired:
        return 124


def _commit(files=(RATE,)):
    """a lost race on coord/state leaves the row in the tree; the next hour's commit carries it"""
    try:
        r = subprocess.run([COMMIT, "count hourly (auto)"] + list(files), timeout=280, capture_output=True, text=True)
    except subprocess.TimeoutExpired:
        print("count_hourly: coord-commit timed out; the row is in the tree for the next commit", file=sys.stderr)
        return 1
    if r.returncode:
        print("count_hourly: coord-commit rc %d: %s" % (r.returncode, r.stderr[-300:]), file=sys.stderr)
    return r.returncode


if __name__ == "__main__":
    sys.exit(run())
