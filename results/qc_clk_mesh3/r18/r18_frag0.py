"""R18 floor: D = AOCV random + distance + |nominal dt| (pair MC mesh skew -> 0, i.e. an ideal shorting level at the
H-tree leaves); union pairs."""
import json, math, sys
pu = json.load(open(sys.argv[1]))
dem = {"|".join(sorted((r["a"], r["b"]))): math.ceil((r["FF"]["aocv_random_ps"] + r["FF"]["aocv_distance_ps"] + abs(r["FF"]["nominal_dt_ps"])) * 10) / 10.0 for r in pu["rows"]}
json.dump(dict(clock=dict(io_hold="plan_demand", hold_demand=dict(source="plan", schema="opentallas.hold_demand.v1",
          basis="R18 floor (mesh MC -> 0)", pairs=dem, landed=[], default_ps=None))), open(sys.argv[2], "w"), indent=1)
v = sorted(dem.values()); print(len(v), v[0], v[len(v)//2], v[-1])
