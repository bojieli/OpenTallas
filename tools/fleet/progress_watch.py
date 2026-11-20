#!/usr/bin/env python3
"""progress_watch: PROGRESS-WATCH-1119 (FABLE-FLOW-1949 detector).  An ALERT only: it never holds, gates, stops or relaunches
anything (owner rules r703/r704).  It reads the kit wave's own record (autopilot/log.txt, plus autopilot/kit_wave_stages.tsv and
autopilot/kit_wave.json when present) and prints / posts one line per finding:

  NO-PROGRESS <die>   a die with eligible rows and no KIT-WAVE LAUNCH for 60 min
  SELF-STOP <die>     the wave REAPed a queue job within 30 min of its own SUBMIT or REAP-REVIVE of that same job
  NO-ADVANCE <die>    an item had 2+ FAIL attempts in 6 h and the later one did not reach a later stage
  STUCK-STATE <die>   current-plan rows CANCELLED/SUPERSEDED with no successor row for 60 min (needs the stages tsv)

A parked die (default hbm, plus kit_wave.json dies.<die>.parked) is reported as PARKED once a day, never alerted.
Each alert is one `bash <coord>/bin/post.sh PROGRESS-WATCH "..."` line, at most one per die per class per hour, and a row in
<coord>/lanes/PROGRESS-WATCH.tsv (the same file is the dedup memory; post.sh commits it with the post).

  python3 -I progress_watch.py                 # live: now = Los Angeles clock, post + append (the 10-min timer)
  python3 -I progress_watch.py --dry-run       # print what would be posted, change nothing
  python3 -I progress_watch.py --replay LOG --from 'YYYY-MM-DD HH:MM' --to 'YYYY-MM-DD HH:MM' [--step 10]
                                               # walk the log in steps, print every alert the live run would have posted
Log times are the hub's Los Angeles wall clock (PST/PDT), compared as naive datetimes."""
import argparse
import csv
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

NO_PROGRESS_MIN = 60
SELF_STOP_MIN = 30
NO_ADVANCE_H = 6
STUCK_MIN = 60
DEDUP_MIN = 60
ACTIVE_LOOKBACK_H = 24
PARKED_DEFAULT = ("hbm",)
STAGE_ORDER = ["kit_rtl", "kit_topology", "pipeline", "prelint", "gen_lint", "gen", "unit", "place", "geom", "grt", "route", "post_cts", "sta", "signoff"]
LINE = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) \w+ AUTOPILOT: (.*)$")
TSV_COLS = ["time", "die", "class", "state", "posted", "text"]


def parse_time(s):
    return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")


def parse_lines(lines):
    """-> event dicts in log order; kind in launch / die_off / no_launch / revive / reap / submit / fail."""
    ev = []
    for ln in lines:
        m = LINE.match(ln.rstrip("\n"))
        if not m:
            continue
        t, rest = parse_time(m.group(1)), m.group(2)
        if rest.startswith("KIT-WAVE LAUNCH "):
            tok = rest.split()[2]
            if "/" in tok:
                ev.append({"t": t, "kind": "launch", "die": tok.split("/")[0], "item": tok.split("/", 1)[1]})
        elif rest.startswith("KIT-WAVE DIE-OFF "):
            ev.append({"t": t, "kind": "die_off", "die": rest.split()[2].rstrip(":")})
        elif rest.startswith("KIT-WAVE NO-LAUNCH "):
            m2 = re.match(r"KIT-WAVE NO-LAUNCH (\S+?): (\d+) eligible", rest)
            if m2:
                ev.append({"t": t, "kind": "no_launch", "die": m2.group(1), "eligible": int(m2.group(2))})
        elif rest.startswith("KIT-WAVE REAP-REVIVE "):
            m2 = re.match(r"KIT-WAVE REAP-REVIVE (\S+?)/(\S+?)@(\d+):.*queue job (\w+) still live", rest)
            if m2:
                ev.append({"t": t, "kind": "revive", "die": m2.group(1), "item": m2.group(2), "attempt": m2.group(3), "job": m2.group(4)})
        elif rest.startswith("KIT-WAVE REAP "):
            m2 = re.match(r"KIT-WAVE REAP (\S+?)/(\S+?)(?:@(\d+))?: (.*?); units \[(.*)\]", rest)
            if m2:
                sup = re.match(r"superseded by attempt (\d+) of the same item", m2.group(4))
                ev.append({"t": t, "kind": "reap", "die": m2.group(1), "item": m2.group(2), "attempt": m2.group(3), "why": m2.group(4),
                           "jobs": re.findall(r"ap-([0-9a-f]+)-a\d+", m2.group(5)), "same_attempt": bool(sup and sup.group(1) == m2.group(3))})
        elif rest.startswith("SUBMIT "):
            p = rest.split()
            if len(p) > 2 and "/" in p[2]:
                ev.append({"t": t, "kind": "submit", "job": p[1], "die": p[2].split("/")[0], "item": p[2].split("/", 1)[1]})
        elif rest.startswith("KIT-WAVE FAIL "):
            m2 = re.match(r"KIT-WAVE FAIL (\S+?)/(\S+) .*? @(\w+)[: ]", rest)
            if m2:
                ev.append({"t": t, "kind": "fail", "die": m2.group(1), "item": m2.group(2), "stage": m2.group(3)})
    return ev


def stage_rank(s):
    return STAGE_ORDER.index(s) if s in STAGE_ORDER else -1


def read_tail(path, since, chunk=8 << 20, max_bytes=96 << 20):
    """text lines of the log from about `since` on; reads backwards in chunks (the log is 80 MB)."""
    size = os.path.getsize(path)
    pos, data = size, b""
    with open(path, "rb") as f:
        while pos > 0 and len(data) < max_bytes:
            new = max(0, pos - chunk)
            f.seek(new)
            data = f.read(pos - new) + data
            pos = new
            try:
                head = data.split(b"\n", 2)[1][:19].decode("ascii", "ignore")
                if parse_time(head) < since:
                    break
            except (ValueError, IndexError):
                pass
    return data.decode("utf-8", "replace").split("\n")


def detect(events, now, state=None, parked=PARKED_DEFAULT):
    """-> [{die, cls, state, text}]; pure.  state (live only) = {eligible: {die: n}, rows: [dict], known: [die], parked: [die]}.
    Without state a die counts as eligible when it launched in the last 24 h (log-only form)."""
    state = state or {}
    out = []
    ev = [e for e in events if e["t"] <= now]
    parked = set(parked) | set(state.get("parked", ()))
    last_launch, dies = {}, set(state.get("known", ()))
    for e in ev:
        if e["kind"] == "launch":
            last_launch[e["die"]] = e["t"]
        if "die" in e:
            dies.add(e["die"])
    # 1. NO-PROGRESS / PARKED
    for die in sorted(dies):
        ll = last_launch.get(die)
        age = (now - ll) if ll else None
        if age is not None and age < timedelta(minutes=NO_PROGRESS_MIN):
            continue
        if die in parked:
            if any(e["kind"] == "die_off" and e["die"] == die and now - e["t"] < timedelta(hours=2) for e in ev):
                out.append({"die": die, "cls": "PARKED", "state": "parked", "text": f"PARKED {die}: DIE-OFF is intentional (parked), not alerting"})
            continue
        elig = state.get("eligible", {}).get(die)
        nl = [e for e in ev if e["kind"] == "no_launch" and e["die"] == die and now - e["t"] <= timedelta(minutes=15)]
        if nl and nl[-1]["eligible"] > (elig or 0):
            elig = nl[-1]["eligible"]  # the wave's own NO-LAUNCH count
        if elig is None:
            if ll is None or age > timedelta(hours=ACTIVE_LOOKBACK_H):
                continue
            elig_txt = "eligible rows not measured (log-only)"
        elif elig <= 0:
            continue
        else:
            elig_txt = f"{elig} eligible rows"
        reasons = {}
        for e in ev:
            if e.get("die") == die and e["kind"] in ("die_off", "no_launch") and (ll is None or e["t"] > ll):
                k = e["kind"].upper().replace("_", "-")
                reasons[k] = reasons.get(k, 0) + 1
        why = ", ".join(f"{k} x{n}" for k, n in sorted(reasons.items())) or "no DIE-OFF / NO-LAUNCH line"
        mins = f"{int(age.total_seconds() // 60)} min" if age is not None else f">{ACTIVE_LOOKBACK_H} h"
        out.append({"die": die, "cls": "NO-PROGRESS", "state": "alert",
                    "text": f"NO-PROGRESS {die}: {elig_txt}, 0 KIT-WAVE LAUNCH for {mins} (last {ll.strftime('%H:%M') if ll else 'none in window'}); {why}"})
    # 2. SELF-STOP: a REAP of a job the wave itself submitted / revived <= 30 min before
    mark, hits = {}, {}
    for e in ev:
        if e["kind"] in ("submit", "revive"):
            mark[e["job"]] = (e["t"], e["kind"])
        elif e["kind"] == "reap":
            for j in e["jobs"]:
                if j in mark and timedelta(0) <= e["t"] - mark[j][0] <= timedelta(minutes=SELF_STOP_MIN):
                    hits.setdefault(e["die"], []).append((e, mark[j][1], e["t"] - mark[j][0]))
    for die, hs in sorted(hits.items()):
        recent = [h for h in hs if now - h[0]["t"] <= timedelta(minutes=DEDUP_MIN)]
        if not recent or die in parked:
            continue
        e, k, dt = recent[-1]
        row = f"{e['item']}@{e['attempt']}" if e.get("attempt") else e["item"]
        out.append({"die": die, "cls": "SELF-STOP", "state": "alert",
                    "text": f"SELF-STOP {die}: {len(recent)} job(s) stopped by the wave {int(dt.total_seconds())} s after its own "
                            f"{'REAP-REVIVE' if k == 'revive' else 'SUBMIT'} (latest {row} at {e['t'].strftime('%H:%M:%S')}: {e['why']})"})
    # 3. NO-ADVANCE: 2+ FAIL attempts of an item in 6 h, the later one not past the earlier stages
    byitem = {}
    for e in ev:
        if e["kind"] == "fail" and now - e["t"] <= timedelta(hours=NO_ADVANCE_H):
            byitem.setdefault((e["die"], e["item"]), []).append(e)
    bad = {}
    for (die, item), fs in byitem.items():
        fs = [f for f in fs if stage_rank(f["stage"]) >= 0]  # only attempts that name a known wave stage
        if len(fs) >= 2 and stage_rank(fs[-1]["stage"]) <= max(stage_rank(f["stage"]) for f in fs[:-1]):
            bad.setdefault(die, []).append((item, len(fs), fs[-1]["stage"], fs[-1]["t"]))
    for die, xs in sorted(bad.items()):
        if die in parked or not any(now - x[3] <= timedelta(minutes=DEDUP_MIN) for x in xs):
            continue
        xs.sort(key=lambda x: -x[1])
        out.append({"die": die, "cls": "NO-ADVANCE", "state": "alert",
                    "text": f"NO-ADVANCE {die}: {len(xs)} item(s) failed 2+ times in {NO_ADVANCE_H} h without a later stage "
                            f"({', '.join(f'{i} x{n}@{s}' for i, n, s, _ in xs[:3])})"})
    # 4. STUCK-STATE: current-plan CANCELLED/SUPERSEDED rows without a successor row for 60 min (stages tsv)
    rows = state.get("rows") or []
    succ = {(r["die"], r["item"]) for r in rows if r.get("status") not in ("CANCELLED", "LINT-ADVISORY")}
    stuck = {}
    for r in rows:
        if r.get("status") == "CANCELLED" and r.get("class") == "SUPERSEDED" and r.get("plan_current") == "yes" and (r["die"], r["item"]) not in succ:
            try:
                if now - datetime.strptime(r["updated"][:16], "%Y-%m-%d %H:%M") >= timedelta(minutes=STUCK_MIN):
                    stuck.setdefault(r["die"], []).append(r)
            except ValueError:
                pass
    for die, rs in sorted(stuck.items()):
        if die not in parked:
            out.append({"die": die, "cls": "STUCK-STATE", "state": "alert",
                        "text": f"STUCK-STATE {die}: {len(rs)} current-plan row(s) CANCELLED/SUPERSEDED with no successor for "
                                f"{STUCK_MIN}+ min (e.g. {rs[0]['item']}, {rs[0]['updated']})"})
    return out


def load_state(coord):
    ap = Path(coord) / "autopilot"
    st = {"parked": [], "known": [], "rows": [], "eligible": {}}
    try:
        for die, v in (json.load(open(ap / "kit_wave.json")).get("dies") or {}).items():
            if isinstance(v, dict):
                st["known"].append(die)
                if v.get("parked"):
                    st["parked"].append(die)
    except (OSError, ValueError):
        pass
    try:
        with open(ap / "kit_wave_stages.tsv", newline="") as f:
            st["rows"] = list(csv.DictReader(f, delimiter="\t"))
    except OSError:
        return st
    # eligible = current-plan rows that were cancelled/superseded and are waiting for a relaunch (not in flight, LINT, WAIT-*, held)
    for r in st["rows"]:
        if r.get("plan_current") == "yes" and r.get("status") == "CANCELLED" and (r.get("class") or "") in ("SUPERSEDED", "QUEUE-CANCELLED", ""):
            st["eligible"][r["die"]] = st["eligible"].get(r["die"], 0) + 1
    for d in st["known"]:
        st["eligible"].setdefault(d, 0)
    return st


def recent_posts(tsv):
    """{(die, class): time of the last row}"""
    seen = {}
    try:
        with open(tsv, newline="") as f:
            for r in csv.DictReader(f, delimiter="\t"):
                try:
                    seen[(r["die"], r["class"])] = datetime.strptime(r["time"], "%Y-%m-%d %H:%M:%S")
                except (ValueError, KeyError):
                    pass
    except OSError:
        pass
    return seen


def dedup(findings, seen, now):
    keep = []
    for f in findings:
        last = seen.get((f["die"], f["cls"]))
        gap = timedelta(hours=24) if f["cls"] == "PARKED" else timedelta(minutes=DEDUP_MIN)
        if last is None or now - last >= gap:
            keep.append(f)
    return keep


def replay(source, start, end, step_min=10, parked=PARKED_DEFAULT, state=None):
    """source = log path or list of lines -> [(time, finding)] exactly as the live run would post them."""
    since = start - timedelta(hours=ACTIVE_LOOKBACK_H + 1)
    events = parse_lines(read_tail(source, since) if isinstance(source, (str, Path)) else source)
    seen, out, t = {}, [], start
    while t <= end:
        for f in dedup(detect(events, t, state, parked), seen, t):
            seen[(f["die"], f["cls"])] = t
            out.append((t, f))
        t += timedelta(minutes=step_min)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--coord", default=os.environ.get("COORD_DIR", os.path.expanduser("~/coord")))
    ap.add_argument("--log")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--replay")
    ap.add_argument("--from", dest="t0")
    ap.add_argument("--to", dest="t1")
    ap.add_argument("--step", type=int, default=10)
    a = ap.parse_args(argv)
    if a.replay:
        for t, f in replay(a.replay, datetime.strptime(a.t0, "%Y-%m-%d %H:%M"), datetime.strptime(a.t1, "%Y-%m-%d %H:%M"), a.step):
            print(f"{t:%Y-%m-%d %H:%M}\t{f['cls']}\t{f['text']}")
        return 0
    from zoneinfo import ZoneInfo
    now = datetime.now(ZoneInfo("America/Los_Angeles")).replace(tzinfo=None, microsecond=0)
    coord = Path(a.coord)
    state = load_state(coord)
    events = parse_lines(read_tail(a.log or str(coord / "autopilot" / "log.txt"), now - timedelta(hours=ACTIVE_LOOKBACK_H + 1)))
    tsv = coord / "lanes" / "PROGRESS-WATCH.tsv"
    found = dedup(detect(events, now, state), recent_posts(tsv), now)
    newfile, posted = not tsv.exists(), 0
    for f in found:
        print(f"{now:%H:%M}\t{f['cls']}\t{f['text']}")
        if a.dry_run:
            continue
        with open(tsv, "a", newline="") as fh:
            w = csv.writer(fh, delimiter="\t", lineterminator="\n")
            if newfile:
                w.writerow(TSV_COLS)
                newfile = False
            w.writerow([f"{now:%Y-%m-%d %H:%M:%S}", f["die"], f["cls"], f["state"], "yes" if f["state"] == "alert" else "no", f["text"]])
        if f["state"] == "alert":
            r = subprocess.run(["bash", str(coord / "bin" / "post.sh"), "PROGRESS-WATCH", "ALERT " + f["text"], "lanes/PROGRESS-WATCH.tsv"],
                               capture_output=True, text=True, timeout=600)
            posted += r.returncode == 0
            if r.returncode:
                print("post failed:", r.stderr.strip()[-300:], file=sys.stderr)
    if found and not posted and not a.dry_run:  # only PARKED rows: commit the tsv ourselves
        subprocess.run(["bash", str(coord / "bin" / "coord-commit.sh"), "PROGRESS-WATCH: parked row", "lanes/PROGRESS-WATCH.tsv"],
                       capture_output=True, text=True, timeout=600)
    return 0


if __name__ == "__main__":
    sys.exit(main())
