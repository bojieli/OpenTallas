#!/usr/bin/env python3
"""C17: per-hard-core orientation search for the G0C core_faces away ports (score per core is independent: R0/MX/MY/R180
keep the core bbox, so partner centres do not move)."""
import sys, json, copy
from pathlib import Path
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/codex-hbm-plan-1351/tools/die_plan")
import check as CK, schema as S
plan = Path(sys.argv[1]).resolve()
rows = json.load(open(sys.argv[2]))
cores = sorted({(r["type"], r["core"]) for r in rows})
raw = S.load(str(plan))
res = {}
for o in ("R0", "MX", "MY", "R180"):
    P = S.Plan(raw, plan)
    for tn, ci in cores:
        for hc in P.types[tn]["hard_cores"]:
            if hc["inst"] == ci:
                hc.setdefault("_orig_orient", hc.get("orient", "R0"))
                hc["orient"] = o
    pc = {}
    R = CK.Report(True)
    # count side warnings per core too
    CK.check_core_faces(P, R, plan.parent, None, max_msgs=10**6, per_core=pc)
    side = {}
    for it in R.items:
        if "about perpendicular" in it["msg"]:
            ci = it["msg"].split(" core ")[1].split(" ")[0]
            side[(it["type"], ci)] = side.get((it["type"], ci), 0) + 1
    for k in cores:
        res.setdefault("%s/%s" % k, {})[o] = pc.get(k, [0, 0]) + [side.get(k, 0)]
    for tn, ci in cores:
        for hc in P.types[tn]["hard_cores"]:
            if hc["inst"] == ci:
                hc["orient"] = hc.pop("_orig_orient")
json.dump(res, open(sys.argv[3], "w"), indent=1)
for k, v in res.items():
    best = min(v, key=lambda o: (v[o][1], v[o][0], v[o][2]))
    print(k, v, "best", best)
