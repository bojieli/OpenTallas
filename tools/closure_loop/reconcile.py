#!/usr/bin/env python3
"""Reconcile the shared experiment register (/home/ubuntu/opentallas-monitor/experiments.json) with reality.

Agents killed by usage limits leave rows saying running/admitted/queued/current for jobs that ended hours ago.  For
every live-claiming row (not this loop's own closure-loop:* rows, untouched for >= --min-age-min), on its host(s):
  ALIVE if any process command line, process cwd or docker container (name, command, mounts) mentions the row's
  worktree path (when that path exists on the host) or one of the row's name tokens, or a PID named in its status
  (PID123 / supervisor123 / driver123 / launcher123 / controller123 / actualPID123) is alive.
  Otherwise DEAD: the row is updated to "terminal (reconciled <time>: no live process/container on <host>; result
  <newest terminal file found>)", which experiment.py drops from the live register (the event log keeps it).
Never kills or touches any process.  Unreachable host -> row left alone.

    reconcile.py [--dry-run] [--min-age-min 90]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import time
from pathlib import Path

MON = Path("/home/ubuntu/opentallas-monitor")
HOSTMAP = {"EPYC1": "ot-epyc1tb", "EPYC2": "ot-epyc2", "EPYC3": "ot-epyc3", "PVE1": "ot-pve1", "AGIDOCK": "ot-agidock128",
           "LOCALHOST": "local", "LOCAL": "local"}
LIVE_RE = re.compile(r"^\s*(running|admitted|queued|active|current|launched|pending|started|waiting|passed|pass\b|PASS|FAIL|"
                     r"preflight)", re.I)
STOP = {"claude", "codex", "route", "routes", "bench", "campaign", "running", "final", "token", "parent", "source", "src",
        "physical", "native", "full", "hold", "margin", "check", "station", "export", "lane"}
ROOTS = "/srv/opentallas-scratch /srv/opentallas-scratch2 /srv/opentallas/scratch-overflow /srv/opentallas/repos /srv/opentallas-scratch2/jobs"
PROBE = r"""
echo '@@PS'; ps -eo pid=,args= 2>/dev/null
echo '@@CWD'; for p in /proc/[0-9]*; do c=$(readlink $p/cwd 2>/dev/null) && echo "${p#/proc/} $c"; done
echo '@@DOCKER'; for c in $(docker ps -q 2>/dev/null); do docker inspect --format '{{.Name}} {{.Config.Cmd}} {{range .Mounts}}{{.Source}} {{end}}' $c; done
echo '@@PATHS'; for d in %s; do test -e "$d" && echo "$d"; done
echo '@@FILES'; timeout 90 find %s -maxdepth 6 \( -name exit -o -name '*.rc' -o -name corner_sta.json -o -name physical.json -o -name signoff.json -o -name summary.txt -o -name result.json \) -mmin -4320 -printf '%%T@ %%p\n' 2>/dev/null
echo '@@END'
"""


def tokens(name):
    """Distinctive tail tokens of a row name (the run label usually ends the name: lockr7, src_u45, ctl16f_u30)."""
    t = {name}
    segs = [x for x in re.split(r"[/:]", name) if x]
    if len(segs) >= 2:
        t.add("/".join(segs[-2:]))
    parts = [p for p in segs[-1].split("-") if p] if segs else []
    for k in (1, 2, 3):
        if len(parts) >= k:
            t.add("-".join(parts[-k:]))
    return {x for x in t if len(x) >= 4 and x.lower() not in STOP and not re.fullmatch(r"r\d+|\d+", x)
            and not re.fullmatch(r"(ot-)?(epyc\d|epyc1tb|pve\d|agidock\d*)", x.lower())}


def probe(host, paths):
    roots = ROOTS + " /home/ubuntu"
    script = PROBE % (" ".join(sorted(set(paths))) or "/nonexistent", ROOTS)
    cmd = ["bash", "-s"] if host == "local" else ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", host, "bash -s"]
    try:
        out = subprocess.run(cmd, input=script, capture_output=True, text=True, timeout=240).stdout
    except subprocess.TimeoutExpired:
        return None
    if "@@END" not in out:
        return None
    sec = {}
    cur = None
    for line in out.splitlines():
        if line.startswith("@@"):
            cur = line[2:]
            sec[cur] = []
        elif cur:
            sec[cur].append(line)
    pids = set()
    for l in sec.get("PS", []):
        w = l.split(None, 1)
        if w:
            pids.add(w[0])
    files = []
    for l in sec.get("FILES", []):
        w = l.split(" ", 1)
        if len(w) == 2:
            files.append((float(w[0]), w[1]))
    return dict(text="\n".join(sec.get("PS", []) + sec.get("CWD", []) + sec.get("DOCKER", [])), pids=pids,
                paths=set(sec.get("PATHS", [])), files=files)


def last_events():
    last = {}
    with open(MON / "experiment-events.jsonl") as f:
        for line in f:
            try:
                e = json.loads(line)
                last[e["experiment"]["name"]] = e["time"]
            except Exception:  # noqa: BLE001
                pass
    return last


def hosts_of(row):
    out = []
    for h in re.split(r"[,\s]+", row.get("host", "")):
        if not h:
            continue
        out.append(HOSTMAP.get(h.upper(), h))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--min-age-min", type=float, default=90)
    a = ap.parse_args()
    rows = json.loads((MON / "experiments.json").read_text())["experiments"]
    last = last_events()
    now = time.time()
    cand = [r for r in rows if LIVE_RE.match(r.get("status", "")) and not r["name"].startswith("closure-loop:")
            and now - last.get(r["name"], 0) >= a.min_age_min * 60]
    byhost = {}
    for r in cand:
        for h in hosts_of(r):
            byhost.setdefault(h, []).append(r)
    probes = {}
    for h, rs in byhost.items():
        wpaths = [r["worktree"].split(":", 1)[-1] for r in rs if r.get("worktree", "").split(":", 1)[-1].startswith("/")]
        probes[h] = probe(h, wpaths)
    stamp = dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    report = dict(time=stamp, candidates=len(cand), alive=[], dead=[], unknown=[])
    for r in cand:
        hs = hosts_of(r)
        if not hs or any(probes.get(h) is None for h in hs):
            report["unknown"].append(r["name"])
            continue
        toks = tokens(r["name"])
        wt = r.get("worktree", "").split(":", 1)[-1]
        spids = set(re.findall(r"(?:PID|pid|supervisor|driver|launcher|controller|simulator)\s*(\d{3,8})", r.get("status", "")))
        alive_on = None
        for h in hs:
            p = probes[h]
            hit = any(t in p["text"] for t in toks) or (wt in p["paths"] and len(wt) > 12 and wt in p["text"]) \
                or bool(spids & p["pids"])
            if hit:
                alive_on = h
                break
        if alive_on:
            report["alive"].append(f"{r['name']} @ {alive_on}")
            continue
        res = []
        for h in hs:
            for t_, f in probes[h]["files"]:
                if any(re.search(r"(^|/)" + re.escape(t) + r"(/|\.|$)", f) for t in toks if len(t) >= 5) \
                        or (len(wt) > 12 and f.startswith(wt.rstrip("/") + "/")):
                    res.append((t_, f"{h}:{f}"))
        res.sort(reverse=True)
        result = res[0][1] if res else "none found"
        status = (f"terminal (reconciled {stamp}: no live process/container on {','.join(hs)}; was "
                  f"'{r['status'][:60]}'; result {result})")
        report["dead"].append(dict(name=r["name"], status=status))
        if not a.dry_run:
            subprocess.run([sys.executable, str(MON / "experiment.py"), "update", "--name", r["name"], "--status", status,
                            "--reason", "closure-loop reconcile: agent dead, no live process/container/terminal claim"],
                           capture_output=True, text=True, timeout=60)
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
