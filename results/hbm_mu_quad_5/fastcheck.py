#!/usr/bin/env python3
"""HBM-MU-QUAD-5 quick pre-gate (not a gate): run check.py G0C hard_cores + core_faces + schema only, in minutes.
Usage: fastcheck.py TOOLS_DIE_PLAN_DIR PLAN_DIR [out.json]"""
import sys, json, time
from pathlib import Path
tools, pd = sys.argv[1], Path(sys.argv[2]); sys.path.insert(0, tools)
import schema as S, check as C
t0 = time.time(); raw = S.load(str(pd / "die_plan.json"))
errs = S.validate(raw); print("schema errors", len(errs)); [print(" ", e) for e in errs[:20]]
P = S.Plan(raw, pd / "die_plan.json"); R = C.Report(True)
C.check_taps_cores(P, R, pd, [])
C.check_core_faces(P, R, pd, None, max_msgs=40)
E = R.errors(); print("hard_cores+core_faces errors", len(E), "t=%.0fs" % (time.time() - t0))
for i in E: print(i["check"], i["msg"][:300])
if len(sys.argv) > 3: Path(sys.argv[3]).write_text(json.dumps([dict(check=i["check"], msg=i["msg"], type=i.get("type")) for i in E], indent=0))
