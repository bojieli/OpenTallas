#!/usr/bin/env python3
"""DIE-HBM-5: run only check.check_taps_cores (G0C hard_cores) on a plan dir. usage: hc_check.py TOOLS PLANDIR"""
import sys, json, collections
sys.path.insert(0, sys.argv[1]); import check as C, schema as S
from pathlib import Path
d = Path(sys.argv[2]); raw = json.loads((d / "die_plan.json").read_text())
R = C.Report(True); P = S.Plan(raw, d / "die_plan.json")
out = C.check_taps_cores(P, R, str(d))
e = [x for x in R.items if x["level"] == "ERROR"]
print("hard_cores ERR", len(e), "off_track", out["core_pins_off_track"])
for x in e: print(x["msg"][:260])
