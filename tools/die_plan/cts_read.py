#!/usr/bin/env python3
"""cts_read.py -- the ONE canonical CTS-stage timing read (TAP-GRID-2130, FABLE-CLOSURE-STRATEGY 21:30 lever 2, every die).

ORFS writes 4_cts_final.rpt and the cts__timing__* metrics of 4_1_cts.json BEFORE the POST_CTS hooks (tap_balance, leaf
affinity ...); the DB that goes on to repair and route is the post-hook one.  Since TAP-GRID-2130 cts_post_report.tcl re-runs
report_metrics after the hooks (log line OT_CTS_FINAL_POSTHOOK); older kits only carry the OT_CTS_POST_TIMING log line and
4_cts_post_hook.rpt (CTS-POST-RPT-1).  Read CTS numbers through this module, never 4_cts_final.rpt / 4_1_cts.json directly:

  cts_timing(path) -> {setup_ws, setup_tns, hold_ws, hold_tns, source, log} or None
      path = a kit dir, a run/logs/.../base dir, a 4_1_cts.log or a 4_1_cts.json.
      source: 'posthook'  (4_1_cts.log OT_CTS_POST_TIMING / rewritten json)
              'prehook'   (only the ORFS pre-hook metric exists: NEVER a clock verdict)
  canonical_report(reports_dir) -> path of the post-hook timing report (4_cts_final.rpt with the marker, else
      4_cts_post_hook.rpt), or None

  python3 -I cts_read.py PATH [...]      one TSV line per path: path source setup_ws hold_ws
"""
import glob
import json
import os
import re
import sys

POST_RE = re.compile(r"^OT_CTS_POST_TIMING setup_ws (\S+) setup_tns (\S+) hold_ws (\S+) hold_tns (\S+)", re.M)
MARK = "OT_CTS_FINAL_POSTHOOK"
LOG_GLOBS = ("run/logs/*/*/base/4_1_cts.log", "gen/*/run/logs/*/*/base/4_1_cts.log", "logs/*/*/base/4_1_cts.log",
             "work/run/logs/*/*/base/4_1_cts.log", "4_1_cts.log")


def _rd(p, n=None):
    try:
        with open(p, errors="replace") as f:
            return f.read() if n is None else f.read(n)
    except OSError:
        return ""


def _num(s):
    try:
        v = float(s)
    except ValueError:
        return None
    return v if v == v and abs(v) < 1e29 else None


def parse_log(text):
    """-> dict of the LAST OT_CTS_POST_TIMING line, else None"""
    m = None
    for m in POST_RE.finditer(text):
        pass
    if not m:
        return None
    return dict(setup_ws=_num(m.group(1)), setup_tns=_num(m.group(2)), hold_ws=_num(m.group(3)), hold_tns=_num(m.group(4)))


def _log_of(path):
    if os.path.isfile(path):
        if path.endswith(".json"):
            return os.path.join(os.path.dirname(path), "4_1_cts.log")
        return path
    for g in LOG_GLOBS:
        c = sorted(glob.glob(os.path.join(path, g)), key=os.path.getmtime)
        if c:
            return c[-1]
    return None


def cts_timing(path):
    log = _log_of(path)
    if log and os.path.isfile(log):
        d = parse_log(_rd(log))
        if d and d["setup_ws"] is not None:
            return dict(d, source="posthook", log=log)
    js = path if str(path).endswith(".json") else (os.path.join(os.path.dirname(log), "4_1_cts.json") if log else None)
    if js and os.path.isfile(js):
        try:
            j = json.loads(_rd(js))
        except ValueError:
            return None
        ws = j.get("cts__timing__setup__ws")
        if isinstance(ws, (int, float)) and not isinstance(ws, bool):
            post = bool(log) and MARK in _rd(log)
            return dict(setup_ws=float(ws), setup_tns=j.get("cts__timing__setup__tns"), hold_ws=j.get("cts__timing__hold__ws"),
                        hold_tns=j.get("cts__timing__hold__tns"), source="posthook" if post else "prehook", log=log)
    return None


def is_posthook_report(path):
    b = os.path.basename(path)
    if b == "4_cts_post_hook.rpt":
        return True
    if b == "4_cts_final.rpt":
        return MARK in _rd(path)
    return False


def canonical_report(reports_dir):
    f = os.path.join(reports_dir, "4_cts_final.rpt")
    if os.path.isfile(f) and is_posthook_report(f):
        return f
    p = os.path.join(reports_dir, "4_cts_post_hook.rpt")
    return p if os.path.isfile(p) else None


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    for p in argv:
        d = cts_timing(p)
        print("\t".join([p, d["source"], str(d["setup_ws"]), str(d["hold_ws"])] if d else [p, "UNMEASURED", "", ""]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
