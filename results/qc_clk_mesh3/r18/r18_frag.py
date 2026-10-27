"""R18: hold-demand fragment from pair_unc.json over the UNION (port-connected + seam) pairs (R17 fragment had seam
pairs only, so 291 port-connected ports fell to default = max demand 116.6).  D = FF total (AOCV + mesh U), as cmd_pairs."""
import json, math, sys
pu = json.load(open(sys.argv[1]))
dem = {"|".join(sorted((r["a"], r["b"]))): math.ceil(r["FF"]["total_ps"] * 10) / 10.0 for r in pu["rows"]}
json.dump(dict(clock=dict(io_hold="plan_demand", hold_demand=dict(source="plan", schema="opentallas.hold_demand.v1",
          basis="R18 union pairs from pair_unc.json (FF total); UNCHECKED", pairs=dem, landed=[], default_ps=None))),
          open(sys.argv[2], "w"), indent=1)
v = sorted(dem.values()); print(len(v), v[0], v[len(v)//2], v[-1])
