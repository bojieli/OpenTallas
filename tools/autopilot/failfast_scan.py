#!/usr/bin/env python3
"""failfast_scan.py -- READ-ONLY dry run of the FAILFAST-1 stop rules over the live jobs of the fleet.

    python3 -I tools/autopilot/failfast_scan.py [--hosts epyc2,epyc4,...] [--json OUT.json] [--timeout 120]

For every OpenROAD global_route / detail_route / cts process on each host it reads the kit's logs and congestion reports and
says which rule WOULD stop it (physical/common_flow/failfast_rules.py), with evidence: log path, GRT rounds / iteration,
overflow trend, DRT violations, hold cap count.  It also lists duplicate live attempts of one item (kit-wave rows: the older
one is the reaper's to stop through the existing wave_jobs judge; other jobs are reported only).
Sends no signal, writes nothing on the hosts (the payload is `python3 -I -c`, ssh -n, ControlPath=none, every call under timeout).
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
RULES = os.path.join(HERE, "..", "..", "physical", "common_flow", "failfast_rules.py")
HOSTSCAN = os.path.join(HERE, "failfast_hostscan.py")
DEFAULT_HOSTS = "epyc2,epyc4,epyc7,epyc8,epyc9,intel1"


def payload():
    """one self-contained `python3 -I -c` program: the rules as module failfast_rules, then the host scan as __main__"""
    rules, host = open(RULES).read(), open(HOSTSCAN).read()
    boot = ("import sys,types\nm=types.ModuleType('failfast_rules')\nexec(%r,m.__dict__)\nsys.modules['failfast_rules']=m\n"
            "exec(compile(%r,'failfast_hostscan.py','exec'),{'__name__':'__main__'})\n" % (rules, host))
    b = base64.b64encode(zlib.compress(boot.encode())).decode()
    return "import base64,zlib;exec(zlib.decompress(base64.b64decode('%s')))" % b


def scan_host(host, timeout=120):
    cmd = ["timeout", str(timeout + 10), "ssh", "-n", "-o", "ControlPath=none", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
           host, "python3 -I -c \"%s\"" % payload()]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 20)
        return json.loads(p.stdout.strip().splitlines()[-1])
    except (subprocess.SubprocessError, ValueError, IndexError) as e:
        return {"host": host, "error": repr(e)[:200], "rows": []}


def duplicates(results):
    """groups of live jobs sharing an item key (+ plan sha), different pids/attempts, across hosts.
    -> [{key, plan_sha, members [(host, pid, attempt, age_h, kit)], older: host:pid, reaper: bool}]
    reaper = every member is a kit-wave row: the older one is for the already-approved wave reaper (wave_jobs.judge) only;
    this tool stops nothing."""
    by = {}
    for res in results:
        for r in res.get("rows", []):
            if r.get("key") and r.get("kit"):
                by.setdefault((r["key"], r.get("plan_sha", "")), {}).setdefault((res["host"], r["pid"]), r)
    out = []
    for (key, sha), rows in by.items():
        # one container runs several stage processes in a row; a pid is one job here
        if len(rows) < 2:
            continue
        mem = sorted(((h, p, r.get("attempt"), r.get("age_h") or 0, r.get("kit")) for (h, p), r in rows.items()), key=lambda m: -m[3])
        kits = {m[4] for m in mem}
        if len(kits) < 2 and len({m[0] for m in mem}) < 2:
            continue                                   # same kit, one host: the watchdog's own second-container check
        out.append({"key": key, "plan_sha": sha, "members": mem, "older": "%s:%s" % (mem[0][0], mem[0][1]),
                    "reaper": key.startswith("wave:")})
    return out


def table(results, dups):
    lines = ["| host | item | stage | age h | detail | WOULD STOP | evidence (log) |", "|---|---|---|---|---|---|---|"]
    n = 0
    for res in results:
        for r in res.get("rows", []):
            if not r.get("verdicts"):
                continue
            for v in r["verdicts"]:
                n += 1
                det = ""
                if r["stage"] == "GRT":
                    det = "iter %s round %s ndr %s series %s" % (r.get("grt_cur"), r.get("grt_rounds"), r.get("grt_ndr"),
                                                                 " ".join("%d:%d" % (a, b) for a, b, _t in r.get("grt_series", [])))
                elif r["stage"] == "DRT":
                    det = "DRT iters %s tail %s" % (r.get("drt_iters"), r.get("drt_tail"))
                else:
                    det = "hold caps %s stall %s" % (r.get("hold_caps"), bool(r.get("hold_stall")))
                lines.append("| %s | %s | %s | %s | %s | %s | %s<br>`%s` |" % (res["host"], r.get("key", "").split(":", 1)[-1], r["stage"],
                             r.get("age_h"), det, v["rule"] + (" (late, now in DRT)" if v.get("late") else ""), v["evidence"][:300], v["log"]))
    if not n:
        lines.append("| - | - | - | - | - | none | - |")
    lines += ["", "Duplicate live attempts:"]
    for d in dups:
        lines.append("- %s sha %s: %s; older %s%s" % (d["key"], d["plan_sha"] or "-", "; ".join("%s:%s att%s %.1fh" % (m[0], m[1], m[2], m[3]) for m in d["members"]),
                                                      d["older"], " (kit-wave rows: reaper path may stop the older)" if d["reaper"] else " (not a wave row: report only)"))
    if not dups:
        lines.append("- none")
    return "\n".join(lines)


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--hosts", default=DEFAULT_HOSTS)
    a.add_argument("--json")
    a.add_argument("--timeout", type=int, default=120)
    x = a.parse_args(argv)
    from concurrent.futures import ThreadPoolExecutor
    hosts = [h for h in x.hosts.split(",") if h]
    with ThreadPoolExecutor(len(hosts)) as ex:
        results = list(ex.map(lambda h: scan_host(h, x.timeout), hosts))
    for h, r in zip(hosts, results):
        r.setdefault("host", h)
    dups = duplicates(results)
    if x.json:
        json.dump({"results": results, "duplicates": dups}, open(x.json, "w"), indent=1)
    print(table(results, dups))
    for r in results:
        if r.get("error"):
            print("SCAN-ERROR %s %s" % (r["host"], r["error"]), file=sys.stderr)
        print("# %s: %d watched jobs, %d would stop" % (r["host"], len(r.get("rows", [])), sum(1 for q in r.get("rows", []) if q.get("verdicts"))), file=sys.stderr)


if __name__ == "__main__":
    main()
