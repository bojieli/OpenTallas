#!/usr/bin/env python3
"""dpl_repair_disp_check.py -- C-REPAIR-BUF-OVER-MACRO (KV-INT-R3/FIRM 11-27, replaces C-FIRM-RESIZE-OVERLAP).

Post-place check on the DPL log (3_5_place_dp.log).  The class: repair_design puts repeaters on top of hard macros, the legaliser moves each
one to the nearest free site (kv3_pc / pc_v1 / pc_v3: 627-1988 repeaters moved 100-256 um, 0 FIRM seats).  The old key (FIRM released = 0)
passed on 15 of the 19 failing types; this one keys on the displacement itself and on the OT_REPAIR_MACRO_CLEAR report line of the fix.

  python3 -I dpl_repair_disp_check.py [--max-um 50] LOG [LOG ...]      LOG = 3_5_place_dp.log (or a run_place.log that holds it)
  exit 0 = every log under the limit, 1 = at least one over, 2 = no 'max displacement' line found in some log.
Per log one line:  PASS|FAIL DPL-REPAIR-DISP <log> max_um=<x> limit=<n> macro_clear=<off|rects=..> firm_released=<n>
"""
import argparse
import re
import sys

MAX_RE = re.compile(r"^max displacement\s+([0-9.]+)\s*u\b", re.M)
RMC_RE = re.compile(r"^OT_REPAIR_MACRO_CLEAR (rects=\d+ cells=\d+ moved=\d+ unresolved=\d+ max_move_um=[0-9.]+)", re.M)
REL_RE = re.compile(r"^OT_CLAND released (\d+) FIRM", re.M)


def check(text, limit=50.0):
    """-> (verdict, max_um | None, macro_clear text, firm_released | None); verdict PASS / FAIL / NODATA"""
    m = MAX_RE.findall(text)
    if not m:
        return "NODATA", None, "off", None
    mx = max(float(x) for x in m[:1])      # the first 'Placement Analysis' block is the detailed_placement one
    rc = RMC_RE.search(text)
    rel = REL_RE.search(text)
    return ("PASS" if mx <= limit else "FAIL"), mx, (rc.group(1) if rc else "off"), (int(rel.group(1)) if rel else None)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-um", type=float, default=50.0)
    ap.add_argument("logs", nargs="+")
    a = ap.parse_args(argv)
    rc = 0
    for p in a.logs:
        try:
            text = open(p, errors="replace").read()
        except OSError as e:
            print(f"NODATA DPL-REPAIR-DISP {p}: {e}")
            rc = max(rc, 2)
            continue
        v, mx, mc, rel = check(text, a.max_um)
        print(f"{v} DPL-REPAIR-DISP {p} max_um={mx} limit={a.max_um:g} macro_clear={mc} firm_released={rel}")
        rc = max(rc, {"PASS": 0, "FAIL": 1, "NODATA": 2}[v])
    return rc


if __name__ == "__main__":
    sys.exit(main())
