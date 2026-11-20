#!/usr/bin/env python3
"""kit_reports.py -- a kit's stage reports are its own (FLOW-FIX-2045, COORD, FABLE-FIX-S81-SERDES: the H23 and H25 kits carried H21's tt_setup_repair_grt.log, same md5, dated before H23 existed;
every reader quoted H21's TT -73.5 as H23's).

A report (a log / verdict file one of the kit's own stage steps writes) is STALE when it is older than the kit's own synthesis start: the earliest mtime of <kit>/run/logs/asap7/*/base/1_*.log
(else run/results/asap7/*/base/1_*), or, when the kit has not synthesised yet, whenever it exists at all (nothing of this kit can have produced it).  cp -a / cp -p / rsync -a keep the mtimes of
the source, so a copied report stays older than the copy's own synthesis; a relayed kit keeps its internal order, so its own reports stay newer than its synthesis.

  kit_reports.py quarantine KIT   move every stale report into KIT/stale_reports/ (run_kit.sh does this first); prints one line per file
  kit_reports.py stale KIT FILE   exit 0 when FILE is a stale report of KIT, 1 when it is the kit's own
Library: synth_start(kit), is_stale(kit, path), quarantine(kit).  Readers call is_stale (or compare to synth_start) before quoting a kit-level report.
"""
import glob
import os
import sys

REPORT_GLOBS = ("tt_setup_repair*.log", "tt_setup_measure*.log", "tt_setup_keep.log", "postcts_gate_*.log", "postcts_gate_*.json", "hold_gate.log", "pregrt_ff_hold*.log",
                "hold_margin_*.log", "run_place.log", "run_route.log", "run_cts.log", "run_grt.log", "run_finish.log", "grt_policy.json", "stage_odb_guard.log",
                "FAIL_POSTCTS", "FAIL_PREFLOOR", "legacy_gate*.log", "hop_census.log", "reg_fanout.log", "face_guard*.json")
SLACK_S = 2.0


def _mt(p):
    try:
        return os.stat(p).st_mtime
    except OSError:
        return None


def synth_start(kit):
    """-> epoch of the kit's own synthesis start, or None when the kit has not synthesised (no run/logs or run/results 1_* file)"""
    ts = []
    for pat in ("run/logs/asap7/*/base/1_*.log", "run/results/asap7/*/base/1_*"):
        ts += [t for t in (_mt(p) for p in glob.glob(os.path.join(kit, pat))) if t is not None]
        if ts:
            break
    return min(ts) if ts else None


def is_stale(kit, path):
    m = _mt(path)
    if m is None:
        return False
    s = synth_start(kit)
    return True if s is None else m < s - SLACK_S


def reports(kit):
    out = []
    for g in REPORT_GLOBS:
        out += [p for p in glob.glob(os.path.join(kit, g)) if os.path.isfile(p) and not os.path.islink(p)]
    return sorted(set(out))


def quarantine(kit, log=print):
    moved = []
    s = synth_start(kit)
    for p in reports(kit):
        m = _mt(p)
        if m is None or not (s is None or m < s - SLACK_S):
            continue
        d = os.path.join(kit, "stale_reports")
        os.makedirs(d, exist_ok=True)
        dst = os.path.join(d, os.path.basename(p))
        if os.path.exists(dst):
            dst += ".%d" % int(m)
        try:
            os.replace(p, dst)
            moved.append((p, dst)); log("KIT_REPORTS quarantined %s (mtime %d %s synth start %s)" % (os.path.basename(p), m, "before" if s else "and no", int(s) if s else "yet"))
        except OSError as e:
            log("KIT_REPORTS keep %s: %s" % (p, e))
    return moved


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    if len(a) == 2 and a[0] == "quarantine":
        quarantine(os.path.abspath(a[1]), lambda m: print(m, file=sys.stderr))
        return 0
    if len(a) == 3 and a[0] == "stale":
        return 0 if is_stale(os.path.abspath(a[1]), a[2]) else 1
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
