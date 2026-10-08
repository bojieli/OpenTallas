#!/usr/bin/env python3
"""Disk admission gate for /srv/opentallas-scratch/admit.sh and ~/bin/admit.sh (fleet disk guard 2026-10-07).

Waits until every root in the host's floor table has at least its floor free, then exits 0.  The table is
/srv/opentallas-scratch/admit_disk.json (or $ADMIT_DISK_JSON): {"roots": {"/": 100, "/srv/opentallas-scratch2": 200}}.
No table -> no gate.  The closure loop applies the same floors (tools/closure_loop/hosts.json min_free_disk_gb +
disk_roots) before it launches; this gate covers jobs started outside the loop."""
import json, os, shutil, sys, time

TABLE = os.environ.get("ADMIT_DISK_JSON", "/srv/opentallas-scratch/admit_disk.json")


def short():
    try:
        roots = json.load(open(TABLE))["roots"]
    except (FileNotFoundError, ValueError, KeyError):
        return []
    out = []
    for path, floor in roots.items():
        try:
            free = shutil.disk_usage(path).free / 2**30
        except FileNotFoundError:
            continue
        if free < floor:
            out.append(f"{path} {free:.0f} GB free < {floor}")
    return out


if __name__ == "__main__":
    while True:
        s = short()
        if not s:
            sys.exit(0)
        print(time.strftime("%FT%T"), "admit_disk: waiting:", "; ".join(s), file=sys.stderr, flush=True)
        time.sleep(60)
