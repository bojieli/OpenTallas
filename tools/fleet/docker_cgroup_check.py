#!/usr/bin/env python3
"""docker_cgroup_check.py -- P-RAIL-BYPASS (COORD 11-27 decision: the cgroup-parent check is RETIRED; memory cap + labels are the mechanism), REPORT ONLY.

A container is accounted by RAM admission and found by ot-run --cancel through two things the ot-heavy-docker shim sets: the label ot.unit=<admitting unit>
(ot-heavy-stop / cancel find it by it, ot-heavy-reconcile attributes its memory to that unit as use.<unit>) and --memory=<declared cap>.  This lists every running
container on the given hosts (default: this host) that has NO ot.unit label or NO memory cap.  It never stops, kills or changes anything; exit 0 always.

  python3 -I docker_cgroup_check.py [--hosts epyc7,epyc8]
"""
import argparse
import json
import re
import subprocess
import sys




def judge(rows):
    """rows: docker inspect dicts -> (ok, bad) lists of (name, why); ok = label ot.unit present AND HostConfig.Memory > 0"""
    ok, bad = [], []
    for r in rows:
        name = (r.get("Name") or r.get("Id", "?")[:12]).lstrip("/")
        labels = (r.get("Config") or {}).get("Labels") or {}
        mem = int((r.get("HostConfig") or {}).get("Memory") or 0)
        why = [w for w, miss in (("no ot.unit label", not labels.get("ot.unit")), ("no memory cap", mem <= 0)) if miss]
        (bad if why else ok).append((name, ", ".join(why)))
    return ok, bad


def inspect_host(host, run=subprocess.run):
    cmd = "ids=$(docker ps -q); [ -n \"$ids\" ] && docker inspect $ids || echo []"
    argv = ["bash", "-c", cmd] if host in ("", "local") else ["ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "-o", "ControlPath=none", host, cmd]
    r = run(argv, capture_output=True, text=True, timeout=90)
    if r.returncode:
        raise RuntimeError(r.stderr.strip()[-200:])
    return json.loads(r.stdout or "[]")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--hosts", default="local")
    a = ap.parse_args(argv)
    for h in a.hosts.split(","):
        try:
            ok, bad = judge(inspect_host(h))
        except Exception as e:                      # noqa: BLE001
            print(f"{h}: cannot inspect: {e}")
            continue
        print(f"{h}: {len(ok)} container(s) with an ot.unit label and a memory cap, {len(bad)} without (REPORT ONLY)")
        for name, why in bad:
            print(f"  - {name}: {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
