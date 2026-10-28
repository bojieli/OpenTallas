import json, sys, collections
from pathlib import Path
sys.path.insert(0, sys.argv[1] + "/tools/die_plan")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import check, schema as S, die_clock as DC, streets as ST
from spread import spread_type
from pathlib import Path
plan = Path(sys.argv[2]); spec = json.loads(sys.argv[3])
raw = S.load(str(plan))
for tn, T, axes in spec.get("spread", []):
    m, over = spread_type(raw["partition_types"][tn], T=T, axes=tuple(axes))
    print("spread", tn, len(m), "outside", over)
for pn, dxy in spec.get("shift_parts", {}).items():
    p = next(p for p in raw["partitions"] if p["name"] == pn)
    p["origin_um"] = [round(p["origin_um"][0] + dxy[0], 4), round(p["origin_um"][1] + dxy[1], 4)]
P = S.Plan(raw, plan)
ko = DC.keepouts(P)
cfg = ST.config(P.die.get("streets"))
geo = {lid: check.lane_geometry(P, lid) for lid in P.lanes}
flows = [(lid, int(P.ports[P.lanes[lid]["ports"][0]]["width"]), [tuple(q) for q in g[0]]) for lid, g in geo.items()] + check.channel_flows(P)
A = ST.analyze(float(P.W), float(P.H), ko, cfg, [], [], [], flows=flows)
over = [c for c in A["cores"] if c["street_dist_um"] is None or c["street_dist_um"] > cfg["reach_um"] + 1e-6]
g = collections.defaultdict(list)
for c in over:
    g[c["name"].split("/")[0]].append((c["name"].split("/")[1], c["street_dist_um"], c["rect_um"]))
for k, v in sorted(g.items()):
    print(k, len(v), v[:4])
print("TOTAL", len(over), "of", len(A["cores"]))
if len(sys.argv) > 4:
    ST.render(A, ko, sys.argv[4], float(P.W), float(P.H), P.name)
    json.dump(raw, open(sys.argv[5], "w")) if len(sys.argv) > 5 else None
if spec.get("probe"):
    import numpy as np
    gg = cfg["raster_um"]
    occ = ST.raster(float(P.W), float(P.H), ko, gg); free = ~occ
    ry, rx = ST.demand(free, gg, flows, cfg)
    RY, RX = ST._runs(free, 0) * gg, ST._runs(free, 1) * gg
    for x, y in spec["probe"]:
        i, j = int(x // gg), int(y // gg)
        print("probe", (x, y), "free", bool(free[j, i]), "req_ew", round(float(ry[j, i]), 2), "run_y", round(float(RY[j, i]), 2),
              "req_ns", round(float(rx[j, i]), 2), "run_x", round(float(RX[j, i]), 2))
