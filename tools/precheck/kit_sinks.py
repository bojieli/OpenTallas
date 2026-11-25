#!/usr/bin/env python3
"""kit_sinks.py -- PRECHECK-1119: the clock-sink count each kit actually saw, for the STALE-BINS check.

  kit_sinks.py [--roots DIR[,DIR]] [--max-age-h 168] > kit_sinks.json
  kit_sinks.py --kitwave [--max-age-h 168] > kit_sinks.json    (kit-wave CTS logs; adds max_tap / max_sinks after the cap pass)

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
CAP = re.compile(r"OT_CLOCK_TAPS cap \d+ sinks/tap: \d+ sinks re-assigned; per tap: (.*)")
RECHECK = re.compile(r"OT_CLOCK_TAPS cap recheck .*?over cap now: (.*)")
KITWAVE = "/srv/opentallas-scratch*/claude/kw43-wave-1109*/runs/*/kit-wave/*/*/{,private/*/}*/gen/*/run/logs/asap7/*/base/4_1_cts.log"


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


def max_tap(lines):
    """(tap, sinks) of the largest tap after the cap pass (the cap line, raised by the hop-latch recheck), or None
    (QC-CB-SPREAD-R2 11-24: the largest tap fanout the kit really built, for ADV-STALE-BINS)"""
    best = None
    for ln in lines:
        m = CAP.search(ln) or RECHECK.search(ln)
        if not m:
            continue
        for part in m.group(1).split(","):
            tok = part.split()
            if len(tok) >= 2:
                try:
                    v = int(tok[-1])
                except ValueError:
                    continue
                if best is None or v > best[1]:
                    best = (tok[-2], v)
    return best


def kit_type(log):
    """the kit type of a kit-wave CTS log path .../gen/<type>/run/logs/..., or None"""
    m = re.search(r"/gen/([^/]+)/run/logs/", str(log))
    return m.group(1) if m else None


def scan_kitwave(pattern=KITWAVE, max_age_h=168):
    """kit-wave kits (the wave and private run-items): per type the newest 4_1_cts.log -> {sinks, taps, max_tap, max_sinks,
    log, mtime}.  The sinks are the clock-net sinks the kit split over its taps (OT_CLOCK_TAPS summary line)."""
    import glob
    out, now, host = {}, time.time(), socket.gethostname()
    pats = [pattern]
    if "{,private/*/}" in pattern:
        pats = [pattern.replace("{,private/*/}", ""), pattern.replace("{,private/*/}", "private/*/")]
    for pat in pats:
        for log in glob.glob(pat):
            tn = kit_type(log)
            try:
                mt = os.path.getmtime(log)
            except OSError:
                continue
            if not tn or now - mt > max_age_h * 3600 or (tn in out and out[tn]["mtime"] >= mt):
                continue
            r = subprocess.run(["grep", "-h", "-e", "OT_CLOCK_TAPS", log], capture_output=True, text=True, timeout=120)
            lines = r.stdout.splitlines()
            v = next((parse_line(ln) for ln in lines if LINE.search(ln)), None)
            if not v:
                continue
            mx = max_tap(lines)
            out[tn] = dict(sinks=v[1], taps=v[0], max_tap=mx[0] if mx else None, max_sinks=mx[1] if mx else None,
                           log=f"{host}:{log}", mtime=mt)
    return out


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
    ap.add_argument("--kitwave", action="store_true", help="scan the kit-wave kits (KITWAVE glob) instead of --roots; records max_tap too")
    a = ap.parse_args(argv)
    res = scan_kitwave(max_age_h=a.max_age_h) if a.kitwave else scan([r for r in a.roots.split(",") if r], a.max_age_h)
    json.dump(res, sys.stdout, indent=1)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
