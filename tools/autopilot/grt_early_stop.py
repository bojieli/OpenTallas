#!/usr/bin/env python3
"""grt_early_stop.py -- optional early stop of a flow GRT that will end in GRT-0116 (lane FLOW-TIME-1, 2026-11-07).

OFF by default: with OT_GRT_EARLY_STOP unset no command reads a kit or touches a process.  Not called by the autopilot,
no flow file changes, so no flow tag or sign-off input changes.

The flow GRT writes congestion-<N>.rpt every 5 extra iterations.  A rule "N:T[,N:T...]" stops a form when the summed
'congestion:' values of report N are >= T.  Measured on 2,594 kit logs (11-03..11-07): 15:10000,20:1000 had no form that
later reached overflow 0, DRT or sign-off above it.  See lanes/COORD-REVIEW-QUEUE.md, FLOW-TIME-1.  Rules were calibrated
on forms placed with routability-driven placement and on the abstracts of that window.

    OT_GRT_EARLY_STOP=15:10000,20:1000 grt_early_stop.py scan KIT...        prints WOULD-STOP lines, changes nothing
    ... OT_GRT_EARLY_STOP_ACT=1 grt_early_stop.py scan --act KIT...         stops the one openroad process of that kit
    grt_early_stop.py replay SCAN.jsonl [--rule 15:10000,20:1000]           the measurement table from a kit log scan

A form that asked for -allow_congestion (KW-FIX-8) is never stopped: DRT decides those.  Run on the kit's host.
"""
import argparse
import glob
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

CONG = re.compile(rb"congestion:(\d+)")
REPORT = re.compile(r"congestion-(\d+)\.rpt$")


def parse_rule(text):
    """'15:10000,20:1000' -> {15: 10000, 20: 1000}; a malformed rule is an error, never a silent default"""
    out = {}
    for part in (text or "").split(","):
        m = re.fullmatch(r"\s*(\d+)\s*:\s*(\d+)\s*", part)
        if not m:
            raise ValueError(f"bad rule item {part!r} (want ITER:OVERFLOW)")
        out[int(m[1])] = int(m[2])
    return out


def decide(reports, rule):
    """reports {iteration: overflow}; -> (iteration, overflow, threshold) of the first rule met, else None"""
    for n in sorted(rule):
        if n in reports and reports[n] >= rule[n]:
            return n, reports[n], rule[n]
    return None


def stage_dirs(kit):
    lg = sorted(glob.glob(os.path.join(kit, "run", "logs", "asap7", "*", "base")))
    return lg[0] if lg else None


def allow_congestion(kit):
    try:
        return bool(re.search(r"^\s*(?:export\s+)?GLOBAL_ROUTE_ARGS\b.*-allow_congestion", (Path(kit) / "config.mk").read_text(), re.M))
    except OSError:
        return False


def reports_of(kit):
    """{iteration: overflow} of THIS GRT run: a report older than the kit's 4_cts.odb belongs to an earlier run"""
    lg = stage_dirs(kit)
    if not lg:
        return {}
    rd = lg.replace("/logs/", "/reports/")
    odb = os.path.join(lg.replace("/logs/", "/results/"), "4_cts.odb")
    since = os.path.getmtime(odb) if os.path.exists(odb) else 0
    out = {}
    for p in glob.glob(os.path.join(rd, "congestion-*.rpt")):
        m = REPORT.search(p)
        try:
            if m and os.path.getmtime(p) >= since:
                out[int(m[1])] = sum(map(int, CONG.findall(Path(p).read_bytes())))
        except OSError:
            pass
    return out


def global_route_over(kit):
    """true when the first global_route of the stage has returned (a later stop would hit repair, not the iterations)"""
    lg = stage_dirs(kit)
    for p in glob.glob(os.path.join(lg or "/nonexistent", "5_1_grt*.log")):
        try:
            if re.search(r"Took \d+ seconds: global_route", Path(p).read_text(errors="replace")):
                return True
        except OSError:
            pass
    return False


def flow_pids(kit):
    """host pids of openroad running global_route in the container whose /work is this kit"""
    ids = subprocess.run(["docker", "ps", "-q"], capture_output=True, text=True, timeout=60).stdout.split()
    if not ids:
        return []
    info = json.loads(subprocess.run(["docker", "inspect"] + ids, capture_output=True, text=True, timeout=120).stdout or "[]")
    pids = []
    for c in info:
        if not any(m.get("Destination") == "/work" and m.get("Source") == kit for m in c.get("Mounts", [])):
            continue
        top = subprocess.run(["docker", "top", c["Id"], "-eo", "pid,args"], capture_output=True, text=True, timeout=60).stdout
        for line in top.splitlines()[1:]:
            pid, _, args = line.strip().partition(" ")
            if re.search(r"(^|/)openroad\b", args) and "global_route" in args:
                pids.append(int(pid))
    return pids


def stop(kit, hit, rule, find=flow_pids, wait_s=30):
    """TERM the single flow process; the marker line carries the GRT-0116 text the autopilot's existing classifier reads.
    -> (stopped, why)"""
    pids = find(kit)
    if len(pids) != 1:
        return False, f"expected one global_route process, found {pids}"
    n, overflow, thr = hit
    rec = dict(tool="grt_early_stop", iteration=n, overflow=overflow, threshold=thr, rule=rule, pid=pids[0], time=time.time())
    (Path(kit) / "grt_early_stop.json").write_text(json.dumps(rec) + "\n")
    os.kill(pids[0], signal.SIGTERM)
    t0 = time.time()
    while time.time() - t0 < wait_s and os.path.exists(f"/proc/{pids[0]}"):
        time.sleep(1)
    logs = sorted(glob.glob(os.path.join(stage_dirs(kit), "5_1_grt*.log")), key=os.path.getmtime)
    if logs:
        with open(logs[-1], "a") as f:
            f.write(f"[ERROR GRT-0116] early stop: overflow {overflow} >= {thr} at iteration {n} (grt_early_stop {rule})\n")
    return True, "stopped"


def scan(kits, act=False, env=os.environ, find=flow_pids):
    """-> printed lines.  Off (no read, no action) without OT_GRT_EARLY_STOP."""
    text = env.get("OT_GRT_EARLY_STOP", "")
    if not text:
        return ["grt_early_stop: off (OT_GRT_EARLY_STOP unset)"]
    rule = parse_rule(text)
    act = act and env.get("OT_GRT_EARLY_STOP_ACT") == "1"
    out = []
    for kit in kits:
        kit = os.path.abspath(kit)
        if allow_congestion(kit):
            out.append(f"SKIP {kit}: -allow_congestion")
            continue
        if global_route_over(kit):
            continue
        hit = decide(reports_of(kit), rule)
        if not hit:
            continue
        line = f"overflow {hit[1]} >= {hit[2]} at iteration {hit[0]} {kit}"
        if act:
            ok, why = stop(kit, hit, text, find=find)
            out.append(f"{'STOPPED' if ok else 'NOT-STOPPED'} {line}" + ("" if ok else f": {why}"))
        else:
            out.append(f"WOULD-STOP {line}")
    return out


def replay_rows(rows, rule):
    """rows: scan records {e, el, mt, extra, tot, drt, so, reps [[n, mtime, gcells, overflow]...]}.  -> counts + hours"""
    tp = fp = other = 0
    saved = 0.0
    fails = 0
    false_stops = []
    for r in rows:
        if not r.get("el"):
            continue
        fail = r.get("e") == "GRT-0116"
        fails += fail
        t0 = r["mt"] - r["el"]
        reps = {x[0]: x for x in r.get("reps", []) if t0 - 60 <= x[1] <= r["mt"] + 60}
        hit = decide({n: x[3] for n, x in reps.items()}, rule)
        if not hit:
            continue
        signed = any(v in ("SIGNED", "LOCAL_PASS_NEEDS_PARENT") for v in r.get("so", []))
        passed = not fail and (bool(r.get("tot")) and r["tot"][0] == 0 or r.get("drt") or signed)
        if fail:
            tp += 1
            saved += r["mt"] - reps[hit[0]][1]
        elif passed:
            fp += 1
            false_stops.append(r.get("k"))
        else:
            other += 1
    return dict(grt0116=fails, caught=tp, false_stops=fp, other=other, saved_h=round(saved / 3600, 1), false_stop_kits=false_stops)


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    s = a.add_subparsers(dest="cmd", required=True)
    p = s.add_parser("scan")
    p.add_argument("--act", action="store_true")
    p.add_argument("kits", nargs="*")
    p = s.add_parser("replay")
    p.add_argument("scan")
    p.add_argument("--rule", default="15:10000,20:1000")
    x = a.parse_args(argv)
    if x.cmd == "scan":
        print("\n".join(scan(x.kits, act=x.act)))
        return 0
    rows = [json.loads(ln) for ln in open(x.scan) if ln.strip()]
    print(json.dumps(replay_rows(rows, parse_rule(x.rule)), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
