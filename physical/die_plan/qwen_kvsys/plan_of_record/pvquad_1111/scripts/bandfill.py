#!/usr/bin/env python3
"""bandfill.py PLAN SIDECAR TYPE OUT_JSON : run clock_landing_plan.fill_failed_bands for one type; write that type's
landing_contract.bands + report (merge afterwards with bandmerge)."""
import json, sys
sys.path.insert(0, sys.argv[5] if len(sys.argv) > 5 else '.')
import clock_landing_plan as CLP
plan, side, tn, out = sys.argv[1:5]
P = json.load(open(plan)); S = json.load(open(side))
new, rep = CLP.fill_failed_bands(P, S, [tn])
json.dump(dict(type=tn, bands=new['partition_types'][tn]['clock']['landing_contract']['bands'], report=rep), open(out, 'w'))
print(tn, 'filled', len(rep))
