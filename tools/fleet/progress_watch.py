#!/usr/bin/env python3
"""progress_watch: PROGRESS-WATCH-1119 (FABLE-FLOW-1949 detector).  An ALERT only: it never holds, gates, stops or relaunches
anything (owner rules r703/r704).  It reads the kit wave's own record (autopilot/log.txt, plus autopilot/kit_wave_stages.tsv and
autopilot/kit_wave.json when present) and prints / posts one line per finding:

  NO-PROGRESS <die>   a die with eligible rows and no KIT-WAVE LAUNCH and no private-spec launch for 60 min
  SELF-STOP <die>     the wave REAPed a queue job within 30 min of its own SUBMIT or REAP-REVIVE of that same job
  NO-ADVANCE <die>    an item had 2+ FAIL attempts in 6 h and the later one did not reach a later stage
  STUCK-STATE <die>   current-plan rows CANCELLED/SUPERSEDED with no successor row for 60 min (needs the stages tsv)
  TICK-DEAD           no autopilot TICK-TIMES line for 20 min (a hung or dead tick; FLOW-OPS-1000)

A parked die (default hbm, plus kit_wave.json dies.<die>.parked) is reported as PARKED once a day, never alerted.
Each alert is one `bash <coord>/bin/post.sh PROGRESS-WATCH "..."` line, at most one per die per class per hour, and a row in
<coord>/lanes/PROGRESS-WATCH.tsv (the same file is the dedup memory; post.sh commits it with the post).

  python3 -I progress_watch.py                 # live: now = Los Angeles clock, post + append (the 10-min timer)
  python3 -I progress_watch.py --dry-run       # print what would be posted, change nothing
  python3 -I progress_watch.py --replay LOG --from 'YYYY-MM-DD HH:MM' --to 'YYYY-MM-DD HH:MM' [--step 10]
                                               # walk the log in steps, print every alert the live run would have posted
Log times are the hub's Los Angeles wall clock (PST/PDT), compared as naive datetimes.
PRIVATE-LAUNCH-1124 (COORD: "no S81 KIT-WAVE launch for 618 min" while S81 launched private c8s kits all evening): private-spec launches
count as launches of their die too: every <coord>/autopilot/private_specs/<LANE>/<die>_<type>_<MMDDhhmmss> dir and every ot-run submit
ledger record (~/.local/state/ot-run/submit.jsonl) whose --dir is a private kit (.../runs/<die>/kit-wave/<die>/.../private/...).
Still an alert only."""
import argparse
import csv
import fnmatch
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

NO_PROGRESS_MIN = 60
DISK_EVIDENCE_MIN = 25     # waves throttle disk refusals to 15 min, plus tick scheduling delay
SELF_STOP_MIN = 30
NO_ADVANCE_H = 6
STUCK_MIN = 60
TICK_DEAD_MIN = 20          # FLOW-OPS-1000: no TICK-TIMES line for this long = the autopilot tick is dead or hung
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
        if rest.startswith("TICK-TIMES "):
            ev.append({"t": t, "kind": "tick"})
        elif rest.startswith("KIT-WAVE LAUNCH "):
            tok = rest.split()[2]
            if "/" in tok:
                dg = re.search(r"event-key (\S+) plan (\S+)", rest)
                ev.append({"t": t, "kind": "launch", "die": tok.split("/")[0], "item": tok.split("/", 1)[1], "digest": dg.groups() if dg else None})
        elif rest.startswith("KIT-WAVE DIE-OFF "):
            ev.append({"t": t, "kind": "die_off", "die": rest.split()[2].rstrip(":")})
        elif rest.startswith("KIT-WAVE LAUNCH-DISK-CAP "):
            disk = re.match(r"KIT-WAVE LAUNCH-DISK-CAP (\S+?)/(\S+): (.*)", rest)
            if disk:
                ev.append({"t": t, "kind": "disk_cap", "die": disk[1], "item": disk[2], "why": disk[3]})
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


DIES = ("s81_head", "s81", "qwen_compute", "qwen_kvsys", "hbm")      # longest first: s81_head_x is s81_head, not s81
SUBMIT_LEDGER = os.path.expanduser("~/.local/state/ot-run/submit.jsonl")
_SPEC_RE = re.compile(r"(?P<rest>.+)_(?P<st>\d{10})$")
_PRIV_DIR_RE = re.compile(r"/runs/(?P<die>[a-z0-9_]+)/kit-wave/(?P=die)/[^/]+/private/(?P<lane>[^/]+)/")


def spec_die(name):
    for d in DIES:
        if name.startswith(d + "_"):
            return d
    return None


def private_spec_events(root, now, since):
    """PRIVATE-LAUNCH-1124: one private_launch event per autopilot/private_specs/<LANE>/<die>_<type>_<MMDDhhmmss> dir (the stamp is the
    launch, hub LA clock; the year is now's, or the one before for a December stamp read in January)"""
    out = []
    try:
        lanes = sorted(os.listdir(root))
    except OSError:
        return out
    for lane in lanes:
        try:
            names = os.listdir(os.path.join(root, lane))
        except OSError:
            continue
        for n in names:
            m = _SPEC_RE.match(n)
            die = spec_die(n)
            if not m or not die:
                continue
            st = m.group("st")
            try:
                t = datetime(now.year, int(st[0:2]), int(st[2:4]), int(st[4:6]), int(st[6:8]), int(st[8:10]))
            except ValueError:
                continue
            if t > now + timedelta(days=1):
                t = t.replace(year=now.year - 1)
            if since <= t <= now:
                out.append({"t": t, "kind": "private_launch", "die": die, "src": f"private_specs/{lane}/{n}"})
    return out


def ledger_private_events(path, now, since, tz="America/Los_Angeles", max_bytes=32 << 20):
    """PRIVATE-LAUNCH-1124: ot-run submits (S81 c8s kits, FAM / FIX lane kits) whose --dir is a private kit of a die -> private_launch events"""
    from zoneinfo import ZoneInfo
    z = ZoneInfo(tz)
    out = []
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            f.seek(max(0, size - max_bytes))
            data = f.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return out
    for ln in data:
        if "/private/" not in ln:
            continue
        try:
            r = json.loads(ln)
            m = _PRIV_DIR_RE.search((r.get("dir") or "") + "/")
            t = datetime.fromtimestamp(float(r["ts"]), z).replace(tzinfo=None)
        except (ValueError, KeyError, TypeError):
            continue
        if m and since <= t <= now:
            out.append({"t": t, "kind": "private_launch", "die": m.group("die"), "src": f"ot-run {r.get('lane') or m.group('lane')} {os.path.basename(r['dir'].rstrip('/'))}"})
    return out


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


def hold_blocker(die, state, now):
    """F5: -> None (nothing known), '' (every hold within its eta, no pending event: stay silent) or the blocker text"""
    pend = (state.get("pending_event") or {}).get(die)
    holds = (state.get("holds") or {}).get(die) or []
    if not pend and not holds:
        return None
    etas, noterm = [], 0
    for h in holds:
        m = re.search(r"\beta\s*[=:]\s*(\d{4}-\d\d-\d\d(?:[ T]\d\d:\d\d)?)", h, re.I)
        if not m:
            noterm += 1
            continue
        s = m.group(1).replace("T", " ")
        try:
            etas.append(datetime.strptime(s, "%Y-%m-%d %H:%M") if " " in s else datetime.strptime(s, "%Y-%m-%d") + timedelta(hours=23, minutes=59))
        except ValueError:
            noterm += 1
    overdue = sum(1 for e in etas if e < now)
    if not pend and holds and not noterm and not overdue:
        return ""
    parts = [f"blocker: plan event {pend} pending (the wave waits for it)"] if pend else []
    if holds:
        parts.append(f"{len(holds)} hold(s): {noterm} without eta, {overdue} overdue" + (f", next eta {min(e for e in etas if e >= now):%m-%d %H:%M}" if any(e >= now for e in etas) else ""))
    return "; ".join(parts)


def detect(events, now, state=None, parked=PARKED_DEFAULT):
    """-> [{die, cls, state, text}]; pure.  state (live only) = {eligible: {die: n}, rows: [dict], known: [die], parked: [die]}.
    Without state a die counts as eligible when it launched in the last 24 h (log-only form)."""
    state = state or {}
    out = []
    ev = [e for e in events if e["t"] <= now]
    # 0. TICK-DEAD (FLOW-OPS-1000, FABLE-FLOW-1000 a): ticks were seen in the window, and none finished for TICK_DEAD_MIN
    ticks = [e["t"] for e in ev if e["kind"] == "tick"]
    if ticks and now - ticks[-1] >= timedelta(minutes=TICK_DEAD_MIN):
        prog = state.get("tick_progress") or ""
        out.append({"die": "autopilot", "cls": "TICK-DEAD", "state": "alert",
                    "text": f"[PROGRESS-WATCH -> COORD] TICK-DEAD: no autopilot TICK-TIMES line since {ticks[-1]:%H:%M:%S} "
                            f"({(now - ticks[-1]).total_seconds() / 60:.0f} min; no launch or classify meanwhile){(' ' + prog) if prog else ''}. "
                            f"Look: systemctl --user status autopilot.service; autopilot/tick_stack.log"})
    parked = set(parked) | set(state.get("parked", ()))
    last_launch, last_private, dies = {}, {}, set(state.get("known", ()))
    for e in ev:
        if e["kind"] == "launch":
            last_launch[e["die"]] = e["t"]
        elif e["kind"] == "private_launch":
            last_private[e["die"]] = e
            continue                                  # a private launch alone never makes a die "known" to the wave checks
        if "die" in e:
            dies.add(e["die"])
    # 1. NO-PROGRESS / PARKED
    for die in sorted(dies):
        ll = last_launch.get(die)
        age = (now - ll) if ll else None
        if age is not None and age < timedelta(minutes=NO_PROGRESS_MIN):
            continue
        lp = last_private.get(die)
        if lp and now - lp["t"] < timedelta(minutes=NO_PROGRESS_MIN):
            continue                                  # PRIVATE-LAUNCH-1124: the die is launching, through private specs
        if die in parked:
            if any(e["kind"] == "die_off" and e["die"] == die and now - e["t"] < timedelta(hours=2) for e in ev):
                out.append({"die": die, "cls": "PARKED", "state": "parked", "text": f"PARKED {die}: DIE-OFF is intentional (parked), not alerting"})
            continue
        elig = state.get("eligible", {}).get(die)
        nl = [e for e in ev if e["kind"] == "no_launch" and e["die"] == die and now - e["t"] <= timedelta(minutes=15)]
        wave_count = nl and nl[-1]["eligible"] >= (elig or 0)
        if wave_count:
            elig = nl[-1]["eligible"]
        if elig is None:
            if ll is None or age > timedelta(hours=ACTIVE_LOOKBACK_H):
                continue
            elig_txt = "eligible rows not measured (log-only)"
        elif elig <= 0:
            continue
        else:
            elig_txt = f"{elig} eligible rows" if wave_count else f"{elig} candidate rows before launch checks"
        reasons = {}
        for e in ev:
            if e.get("die") == die and e["kind"] in ("die_off", "no_launch") and (ll is None or e["t"] > ll):
                k = e["kind"].upper().replace("_", "-")
                reasons[k] = reasons.get(k, 0) + 1
        disk = next((e for e in reversed(ev) if e.get("die") == die and e["kind"] == "disk_cap"
                     and now - e["t"] <= timedelta(minutes=DISK_EVIDENCE_MIN) and (ll is None or e["t"] > ll)), None)
        details = [f"{k} x{n}" for k, n in sorted(reasons.items())]
        if disk:
            details.append(f"latest disk admission blocked {disk['item']}: {disk['why'][:270]}")
        # F5 (FLOW-OPS-R2 11-22, FABLE-FLOW-0000: "no current launch blocker logged" while the r17b plan event was pending): name the pending plan
        # event and the holds; holds that all carry a future eta (and no pending event) keep the alert silent.
        blk = hold_blocker(die, state, now)
        if blk == "":
            continue
        if blk:
            details.insert(0, blk)
        why = "; ".join(details) or "no current launch blocker logged"
        mins = f"{int(age.total_seconds() // 60)} min" if age is not None else f">{ACTIVE_LOOKBACK_H} h"
        out.append({"die": die, "cls": "NO-PROGRESS", "state": "alert",
                    "text": f"NO-PROGRESS {die}: {elig_txt}, 0 KIT-WAVE LAUNCH for {mins} (last {ll.strftime('%H:%M') if ll else 'none in window'}) "
                            f"and 0 private-spec launches for {NO_PROGRESS_MIN} min (last {lp['t'].strftime('%H:%M') + ' ' + lp['src'][:80] if lp else 'none in window'}); {why}"})
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
    # 3. NO-ADVANCE: 2+ attempts of an item in 6 h that ended on the SAME failing stage with an UNCHANGED input digest
    #    (digest = event-key + plan@sha of the LAUNCH the attempt came from).  Live: only items with a current-plan row in the stages tsv.
    cur = {(r["die"], r["item"]) for r in state.get("rows") or [] if r.get("plan_current") == "yes"}
    dig, byitem = {}, {}
    for e in ev:
        if e["kind"] == "launch":
            dig[(e["die"], e["item"])] = e["digest"]
        elif e["kind"] == "fail" and now - e["t"] <= timedelta(hours=NO_ADVANCE_H) and stage_rank(e["stage"]) >= 0:
            if not state.get("rows") or (e["die"], e["item"]) in cur:
                byitem.setdefault((e["die"], e["item"]), []).append((e, dig.get((e["die"], e["item"]))))
    bad = {}
    for (die, item), fs in byitem.items():
        groups = {}
        for e, d in fs:
            groups.setdefault((e["stage"], d), []).append(e)
        n, g = max(((len(v), k) for k, v in groups.items()), key=lambda x: x[0])
        if n >= 2:
            last = max(e["t"] for e in groups[g])
            bad.setdefault(die, []).append((item, n, g[0], last))
    for die, xs in sorted(bad.items()):
        if die in parked or not any(now - x[3] <= timedelta(minutes=DEDUP_MIN) for x in xs):
            continue
        xs.sort(key=lambda x: -x[1])
        out.append({"die": die, "cls": "NO-ADVANCE", "state": "alert",
                    "text": f"NO-ADVANCE {die}: {len(xs)} item(s) with 2+ attempts in {NO_ADVANCE_H} h ending on the same failing stage "
                            f"with an unchanged input digest ({', '.join(f'{i} x{n}@{s}' for i, n, s, _ in xs[:3])})"})
    # 4. STUCK-STATE: current-plan CANCELLED/SUPERSEDED rows without a successor row for 60 min (stages tsv)
    rows = state.get("rows") or []
    succ = {(r["die"], r["item"]) for r in rows if r.get("status") not in ("CANCELLED", "LINT-ADVISORY")}
    stuck = {}
    for r in rows:
        # FLOW-FIX-2045: a row whose type is signed on this plan block is terminal (the wave prints "signed off on this plan block" and never relaunches it) and a row retired by OWNER r711
        # (resign-defer) waits for spare capacity on purpose; neither is stuck (16 s81 / 18 s81_head rows read STUCK-STATE although 28 of 34 were signed)
        if r.get("_terminal") or r.get("_launch_held"):
            continue
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
    configured_pending = {}
    launch_holds = {}
    try:
        tp = json.load(open(ap / ".tick.progress"))
        if not tp.get("done"):
            st["tick_progress"] = "running tick started %s, last mark '%s'" % (
                datetime.fromtimestamp(float(tp.get("start") or 0)).strftime("%H:%M:%S"), tp.get("phase"))
    except (OSError, ValueError, TypeError):
        pass
    try:
        for die, v in (json.load(open(ap / "kit_wave.json")).get("dies") or {}).items():
            if isinstance(v, dict):
                st["known"].append(die)
                pending = v.get("event_pending")
                if isinstance(pending, dict) and pending.get("event"):
                    configured_pending[die] = str(pending["event"])
                if v.get("parked"):
                    st["parked"].append(die)
                if isinstance(v.get("hold_items"), dict) and v["hold_items"]:
                    launch_holds[die] = v["hold_items"]
                    st.setdefault("holds", {})[die] = [str(x) for x in v["hold_items"].values()]
    except (OSError, ValueError):
        pass
    try:
        with open(ap / "kit_wave_stages.tsv", newline="") as f:
            st["rows"] = list(csv.DictReader(f, delimiter="\t"))
    except OSError:
        return st
    try:
        _ks = json.load(open(ap / "kit_wave_state.json"))
        for die, event in configured_pending.items():
            # The wave keeps the historical log marker after an event is applied.
            if (_ks.get("event_pending_log") or {}).get(die) == f"wait:{event}":
                st.setdefault("pending_event", {})[die] = event
    except (OSError, ValueError, AttributeError):
        pass
    try:
        items = json.load(open(ap / "kit_wave_state.json")).get("items") or {}
        done = {(r.get("die"), r.get("item"), str(r.get("event") or "")) for r in items.values()
                if r.get("q_status") in ("SIGNED", "SIGNED-LINKED") or r.get("retire") == "resign-defer"}
        for r in st["rows"]:
            if (r.get("die"), r.get("item"), r.get("event") or "") in done:
                r["_terminal"] = "1"
    except (OSError, ValueError):
        pass
    # eligible = current-plan rows that were cancelled/superseded and are waiting for a relaunch (not in flight, LINT, WAIT-*, held)
    for r in st["rows"]:
        holds = launch_holds.get(r.get("die"), {})
        item = r.get("item") or ""
        held = next((reason for pat, reason in holds.items() if fnmatch.fnmatchcase(item, pat)), None)
        if held:
            r["_launch_held"] = True
            continue
        cls = r.get("class") or ""
        if cls == "QUEUE-CANCELLED" and ": CANCEL-DESIGN: " in (r.get("reason") or ""):
            # The design watchdog records terminal failures with the generic queue cancellation class.
            continue
        if r.get("plan_current") == "yes" and r.get("status") == "CANCELLED" and cls in ("SUPERSEDED", "QUEUE-CANCELLED", ""):
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
    since = now - timedelta(hours=ACTIVE_LOOKBACK_H + 1)
    events += private_spec_events(str(coord / "autopilot" / "private_specs"), now, since) + ledger_private_events(SUBMIT_LEDGER, now, since)
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
