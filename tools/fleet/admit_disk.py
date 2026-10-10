#!/usr/bin/env python3
"""Disk admission gate for /srv/opentallas-scratch/admit.sh and ~/bin/admit.sh (fleet disk guard 2026-10-07).

Waits until the job's own filesystem has its floor free, then exits 0.  The floor table is
/srv/opentallas-scratch/admit_disk.json (or $ADMIT_DISK_JSON): {"roots": {"/": 100, "/srv/opentallas-scratch2": 200}}.
No table -> no gate.  The closure loop applies the same floors (tools/closure_loop/hosts.json min_free_disk_gb +
disk_roots) before it launches; this gate covers jobs started outside the loop.

PER-DISK (drive-1010 2026-10-10): a job is judged by the disk its working directory actually lives on
($ADMIT_DISK_PATH, else the current directory): only table roots on that same filesystem apply, plus "/" (shared
tmp / docker).  EPYC1's benches under /srv/opentallas (2.7 TB free) were refused because /srv/opentallas-scratch
(another disk) was at 96 %.  A job dir on a disk with no table root gets DEFAULT_FLOOR_GB.  ADMIT_DISK_ALL=1 restores
the old every-root check."""
import json, os, shutil, sys, time

TABLE = os.environ.get("ADMIT_DISK_JSON", "/srv/opentallas-scratch/admit_disk.json")
DEFAULT_FLOOR_GB = 200


def _dev(path):
    while path and not os.path.exists(path):
        path = os.path.dirname(path.rstrip("/")) or "/"
    try:
        return os.stat(path).st_dev
    except OSError:
        return None


def short(job_path=None):
    try:
        roots = json.load(open(TABLE))["roots"]
    except (FileNotFoundError, ValueError, KeyError):
        return []
    job_path = job_path or os.environ.get("ADMIT_DISK_PATH") or os.getcwd()
    check = dict(roots)
    if os.environ.get("ADMIT_DISK_ALL") != "1":
        jdev = _dev(job_path)
        check = {p: f for p, f in roots.items() if p == "/" or (jdev is not None and _dev(p) == jdev)}
        if jdev is not None and not any(_dev(p) == jdev for p in check if p != "/") and _dev("/") != jdev:
            check[job_path] = DEFAULT_FLOOR_GB
    out = []
    for path, floor in check.items():
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
