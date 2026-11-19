#!/usr/bin/env python3
"""kit_sinks.py -- PRECHECK-1119: the clock-sink count each kit actually saw, for the STALE-BINS check.

  kit_sinks.py [--roots DIR[,DIR]] [--max-age-h 168] > kit_sinks.json

Scans kit run directories (default /srv/opentallas-scratch2/claude/ot-jobs/<type>-<stage>-...) for the CTS log line
of clock_taps.tcl, `OT_CLOCK_TAPS <n> taps, <m> sinks moved off <root>: <tap> <count> ...`, and reports per type the
newest one: {type: {sinks: sum of the per-tap counts, taps, log, mtime}}.  Light (grep only); run it on each gen host and
merge the JSON (precheck --kit-sinks takes several files).
"""
import argparse
import json
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOTS = "/srv/opentallas-scratch2/claude/ot-jobs"
LINE = re.compile(r"OT_CLOCK_TAPS (\d+) taps, (\d+) sinks moved off (\S+): (.*)")
STAGE = re.compile(r"^(.+?)-(route|place|cts|grt|kit|sign|signoff|flow|full)-")


def parse_line(ln):
    """(taps, total sinks) of an OT_CLOCK_TAPS summary line, or None"""
    m = LINE.search(ln)
    if not m:
        return None
    toks = m.group(4).split()
    total = 0
    for i in range(0, len(toks) - 1, 2):
        try:
            total += int(toks[i + 1].rstrip(","))
        except ValueError:
            break
    return int(m.group(1)), total


def type_of(dirname):
    m = STAGE.match(dirname)
    return m.group(1) if m else None


def scan(roots, max_age_h):
    out = {}
    now = time.time()
    host = socket.gethostname()
    for root in roots:
        if not os.path.isdir(root):
            continue
        for d in sorted(os.listdir(root)):
            tn = type_of(d)
            p = os.path.join(root, d)
            if not tn or not os.path.isdir(p) or now - os.path.getmtime(p) > max_age_h * 3600:
                continue
            r = subprocess.run(["grep", "-rIh", "-m1", "--include=*.log", "-e", "OT_CLOCK_TAPS [0-9]* taps, ", p],
                               capture_output=True, text=True, timeout=120)
            best = None
            for ln in r.stdout.splitlines():
                v = parse_line(ln)
                if v and (best is None or v[1] > best[1]):
                    best = v
            if not best:
                continue
            mt = os.path.getmtime(p)
            if tn not in out or mt > out[tn]["mtime"]:
                out[tn] = dict(sinks=best[1], taps=best[0], log=f"{host}:{p}", mtime=mt)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--roots", default=ROOTS)
    ap.add_argument("--max-age-h", type=float, default=168)
    a = ap.parse_args(argv)
    json.dump(scan([r for r in a.roots.split(",") if r], a.max_age_h), sys.stdout, indent=1)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
