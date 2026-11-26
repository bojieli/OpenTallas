#!/usr/bin/env python3
"""P-ECO-TIMER-MISMATCH (QC-DRT-ECO-R2 11-26).  An ECO pass dir iN carries the FF (BC) 6_report.json; the TT pass is iNt.  Reading iN/6_report.json
as "setup" and comparing it with the sign-off TT worst slack reported a +11.67 vs -239.72 "timer mismatch" (slw_hc1), +48.48 vs -89.87 (native59),
+66.31 vs -72.62 (sle_hc0).  There is no SDC or latency difference: the 6_report liberty corner is `bc`, and signoff.json corners.ff.sdc_wns_max is the
SAME number (+11.67 / +48.48 / +66.31 exactly, 8 of 8 passes checked).  This check pairs them by corner and only flags a gap on the SAME corner.

  python3 -I eco_corner_check.py PASS_DIR [--max-gap-ps 20]   exit 0 MATCH, 1 MISMATCH (real same-corner timer difference), 2 unreadable
  tt_gain(base_signoff_json, new_signoff_json)                 P-ECO-NO-GAIN measure: TT sdc_wns_max gain in % of the base violation (never 6_report)
"""
import glob
import json
import re
import sys
from pathlib import Path


def report_corner(log_text):
    """liberty corner of an ORFS 6_report.log: bc -> ff, tc -> tt, wc -> ss; None when no read_liberty line"""
    m = re.search(r"read_liberty -corner (\w+)", log_text)
    return {"bc": "ff", "tc": "tt", "wc": "ss"}.get(m.group(1), m.group(1)) if m else None


def check(pass_dir, max_gap=20.0):
    d = Path(pass_dir)
    logs = sorted(glob.glob(str(d / "run/logs/asap7/*/base/6_report.log")))
    if not logs:
        return dict(verdict="UNREADABLE", why="no 6_report.log")
    try:
        corner = report_corner(Path(logs[0]).read_text(errors="replace"))
        ws = json.loads(Path(logs[0][:-4] + ".json").read_text())["finish__timing__setup__ws"]
        so = json.loads((d / "signoff/signoff.json").read_text())["corners"]
    except (OSError, ValueError, KeyError) as e:
        return dict(verdict="UNREADABLE", why=repr(e)[:120])
    if corner not in so or so[corner].get("sdc_wns_max") is None:
        return dict(verdict="UNREADABLE", why="no sign-off corner %s" % corner, corner=corner)
    ref = float(so[corner]["sdc_wns_max"])
    gap = abs(float(ws) - ref)
    return dict(verdict="MATCH" if gap <= max_gap else "MISMATCH", corner=corner, report_ws=ws, signoff_same_corner_ws=ref, gap_ps=round(gap, 2),
                signoff_other={c: v.get("sdc_wns_max") for c, v in so.items() if c != corner})


def tt_gain(base, new):
    """% of the base TT setup violation recovered by the pass (negative = worse); None when the base is not violating"""
    b = float(json.loads(Path(base).read_text())["corners"]["tt"]["sdc_wns_max"])
    n = float(json.loads(Path(new).read_text())["corners"]["tt"]["sdc_wns_max"])
    return None if b >= 0 else round((n - b) / -b * 100.0, 1)


def main(argv=None):
    a = list(argv if argv is not None else sys.argv[1:])
    gap = float(a[a.index("--max-gap-ps") + 1]) if "--max-gap-ps" in a else 20.0
    r = check(a[0], gap)
    print(json.dumps(r))
    return {"MATCH": 0, "MISMATCH": 1}.get(r["verdict"], 2)


if __name__ == "__main__":
    sys.exit(main())
