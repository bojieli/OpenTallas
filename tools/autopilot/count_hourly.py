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
FRESH_S = 30 * 60
SCAN_TIMEOUT_S = 25 * 60
DIES = (("s81", "s81"), ("s81_head", "head"), ("qwen_compute", "qc"), ("qwen_kvsys", "kv"), ("hbm", "hbm"))


VARIANT = re.compile(r"__(a\d+_\d{4}|legalrows_\d+)$")   # AUTO-EXPORT / re-sign name suffixes: the same type as the bare name, not a new unit
INDEX_DIES = {die for die, _ in DIES}


def index_rows(index_json):
    """-> [(die, element, kind)] of the ARCHIVED rows of the AGIdock INDEX.tsv the counter mirrored in agidock_archive_index.json"""
    try:
        a = json.loads(Path(index_json).read_text())
    except (OSError, ValueError):
        return []
    rows = []
    for ln in (a.get("agidock_index_tsv") or "").splitlines()[1:]:
        f = ln.split("\t")
        if len(f) > 10 and f[0] in INDEX_DIES and f[10].startswith(("ARCHIVED", "RTX-FULL-AGI-META")):
            rows.append((f[0], f[1], f[2]))
    return rows


def any_plan_extra(cache, rows, by_die=False):
    """signed units on SOME plan that the current plan does not hold: distinct archived (die, element) whose name is no plan type / type module /
    hard core / counted type / core of that die's counted plan, and not a suffix variant of one that is.  COUNT-DIAG-1118: the last 80 INDEX rows
    were old-plan names (QC sta_region_nb0_*, S81 ot_s81_svc_*, KV hub-C split children) that count for no current plan but are signed."""
    known = {}
    for e in (cache.get("plans") or {}).values():
        k = known.setdefault(e.get("die"), set())
        for t, m in (e.get("plan_types") or {}).items():
            k.add(t); k.add(m)
        for x in (e.get("hard_cores") or []):
            k.add(x)
        for x in list(e.get("signed_types") or {}) + list(e.get("signed_cores") or {}):
            k.add(x)
    seen = set()
    for die, el, kind in rows:
        k = known.get(die, set())
        if el in k or VARIANT.sub("", el) in k:
            continue
        seen.add((die, VARIANT.sub("", el)))
    if by_die:
        short = dict(DIES)
        out = {}
        for die, _ in seen:
            out[short.get(die, die)] = out.get(short.get(die, die), 0) + 1
        return out
    return len(seen)


def rate_row(cache, stamp, extra=0):
    """'YYYY-MM-DD HH:MM total s81=37 head=4+5t ... any=NNN auto'.  total = designs + directly signed types per die that MATCH THE CURRENT PLAN
    (the counter matches type names against the counted plan and keeps a renamed type whose plan block digest is unchanged, the same
    real-inputs test as WAVE-FLOW-R2 row_inputs_unchanged).  any=N adds the signed modules whose records exist but whose pins/outline no longer
    match a current plan design (design_unmatched): signed on some plan.  COORD r711 11-18: both numbers on every run and in every row."""
    by = extra if isinstance(extra, dict) else {}
    extra = sum(by.values()) if isinstance(extra, dict) else extra
    total, any_extra, parts = 0, extra, []
    for die, short in DIES:
        d = t = 0
        for e in (cache.get("plans") or {}).values():
            if e.get("die") == die:
                d += len(e.get("signed_designs") or {})
                t += len(e.get("signed_types") or {})
        total += d + t
        parts.append("%s=%d%s" % (short, d, "+%dt" % t if t else ""))
    dfr = " defer=" + ",".join("%s:%d" % (k, v) for k, v in sorted(by.items()) if v) if any(by.values()) else ""
    return "%s %d %s any=%d%s auto" % (stamp, total, " ".join(parts), total + any_extra, dfr)


def headline(row):
    """COORD r711: 'signed any plan 450 | current plan 395 | deferred re-sign 55 (s81 n, qc n)' from a SIGN-RATE row; the deferred backlog =
    signed on an older plan block, superseded on the current plan, not re-signed (per die from the AGIdock INDEX, the source of truth)"""
    m = re.match(r"^\S+ \S+\s+(\d+)\s", row or "")
    a = re.search(r"\bany=(\d+)", row or "")
    if not m:
        return ""
    cur = int(m.group(1))
    anyn = int(a.group(1)) if a else cur
    d = re.search(r"\bdefer=(\S+)", row or "")
    per = ", ".join(x.replace(":", " ") for x in d.group(1).split(",")) if d else ""
    return "signed any plan %d | current plan %d | deferred re-sign %d%s" % (anyn, cur, anyn - cur, " (%s)" % per if per else "")


def counts_of(row):
    return re.sub(r"\s+auto\s*$", "", row.split(" ", 2)[2]) if row.count(" ") >= 2 else ""


DROP_FRAC = 0.85


def last_total(text):
    for r in reversed((text or "").splitlines()):
        m = re.match(r"^\d{4}-\d\d-\d\d \d\d:\d\d\s+(\d+)\s+s81=", r)
        if m:
            return int(m.group(1))
    return 0


def same_hour_same_counts(text, row):
    hour = row[:13]
    return any(r.startswith(hour) and counts_of(r) == counts_of(row) for r in (text or "").splitlines())


def read_cache():
    return json.loads(CACHE.read_text())


def run(now=None, scan=None, commit=None, force=None):
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
    if force is None:
        force = "--force" in sys.argv[1:]   # COUNT-DIAG-1118: --force used to be ignored, a cache under 30 min old was read as is
    if force or before is None or now - before >= FRESH_S:
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
    row = rate_row(cache, time.strftime("%Y-%m-%d %H:%M", time.localtime(now)), any_plan_extra(cache, index_rows(CACHE.with_name("agidock_archive_index.json")), by_die=True))
    p = COORD / RATE
    last = last_total(p.read_text() if p.exists() else "")
    total = int(row.split(" ")[2])
    if last and total < DROP_FRAC * last:
        print("count_hourly: total %d is more than %d%% under the last row %d: a degraded scan, no row (cache generated %s)"
              % (total, round((1 - DROP_FRAC) * 100), last, time.strftime("%H:%M:%S", time.localtime(float(cache.get("generated") or 0)))), file=sys.stderr)
        print(row)
        return 1
    if same_hour_same_counts(p.read_text() if p.exists() else "", row):
        print("count_hourly: this hour already holds these counts: " + row)
        return 0
    with open(p, "a") as f:
        f.write(row + "\n")
    print(row)
    print("count_hourly: " + headline(row))
    return (commit or _commit)()


def _scan():
    try:
        return subprocess.run([sys.executable, COUNTER, "--force"], cwd=str(COORD), timeout=SCAN_TIMEOUT_S,
                              stdout=subprocess.DEVNULL).returncode
    except subprocess.TimeoutExpired:
        return 124


def _commit():
    """a lost race on coord/state leaves the row in the tree; the next hour's commit carries it"""
    try:
        r = subprocess.run([COMMIT, "count hourly (auto)", RATE], timeout=280, capture_output=True, text=True)
    except subprocess.TimeoutExpired:
        print("count_hourly: coord-commit timed out; the row is in the tree for the next commit", file=sys.stderr)
        return 1
    if r.returncode:
        print("count_hourly: coord-commit rc %d: %s" % (r.returncode, r.stderr[-300:]), file=sys.stderr)
    return r.returncode


if __name__ == "__main__":
    sys.exit(run())
