#!/usr/bin/env python3
"""docker_cgroup_check.py -- P-RAIL-BYPASS (COORD 11-27 ruling 3), REPORT ONLY.

Docker inside ot-run is allowed only with --cgroup-parent set to the ot-run unit, so RAM admission and the cancel path still see the container.  This lists
every running container on the given hosts (default: this host) whose HostConfig.CgroupParent is empty or does not name an ot-run / ot-heavy unit.  It never
stops, kills or changes anything; exit 0 always (a refusal mode needs a later ruling).

  python3 -I docker_cgroup_check.py [--hosts epyc7,epyc8]
"""
import argparse
import json
import re
import subprocess
import sys

UNIT_RE = re.compile(r"(^|/)(oth-|ot-run|ot-heavy|ot-job)[\w@.\\:-]*")


def judge(rows):
    """rows: [{'Name','Id','HostConfig':{'CgroupParent'}}] -> (ok, bad) lists of (name, cgroup_parent)"""
    ok, bad = [], []
    for r in rows:
        name = (r.get("Name") or r.get("Id", "?")[:12]).lstrip("/")
        cgp = ((r.get("HostConfig") or {}).get("CgroupParent") or "")
        (ok if UNIT_RE.search(cgp) else bad).append((name, cgp))
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
        print(f"{h}: {len(ok)} container(s) under an ot-run unit cgroup, {len(bad)} without (REPORT ONLY)")
        for name, cgp in bad:
            print(f"  - {name} cgroup-parent={cgp or '(none)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
