#!/usr/bin/env python3
"""PG-ACTIVITY-KVHBM (10-27): HBM measured-activity load map.  Replaces the SM blocks (old 2.1787 W/mm2, rect area =
32 hnx_rp3lp3h halves = the SM slot hard-core area) of bump-survey hbm_loads.json by the measured SM density; other
blocks are kept at their 10-24 estimate (UNCHECKED-ESTIMATE, not activity-measured).
  make_hbm_map.py OLD_LOADS.json DETAIL.json OUT_LOADS.json"""
import json, sys
old, det, outp = sys.argv[1:4]
L = json.load(open(old)); D = json.load(open(det))
sm = D["sm_slot"]["w_mm2_meas_cts"]
out = []; n = 0
for r, d in L:
    if abs(d - 2.1787) < 1e-4: out.append([r, round(sm, 4)]); n += 1
    else: out.append([r, d])
json.dump(out, open(outp, "w"))
print("replaced", n, "SM rects ->", round(sm, 4), "W/mm2; kept", len(L) - n)
