import json, sys
from pathlib import Path
repo, plan, tn, inst = sys.argv[1:5]
sys.path.insert(0, repo + "/tools/die_plan")
import core_place as CP, route_supply as RS
P = json.load(open(plan)); t = P["partition_types"][tn]
RS.REF_DIRS[:] = [str(Path(plan).parent)]
conns = RS.load_conns(Path(plan).parent, None, Path(plan).parent, [])
cfg = dict(gap=34.56, sweeps=0, topk=4, lam=4.0, reach=360.0, grid_um=21.6, grt_halving="full", fixed_re="", rs=dict(RS.DEFAULTS), timing="class")
M = CP.TypeModel(tn, t, Path(plan).parent, Path(repo), conns, cfg); M.init_limits()
k = M.cid[M.idx[inst]]
print("bands", len(M.bands), "FR", len(M.FR), M.FR[:6] if len(M.FR) else "")
for y in (25.92, 60.48, 120.96, 190.08, 300.24):
    row = []
    for x in range(26, 1540, 43):
        x = CP.snap(x)
        row.append("." if M.legal(k, x, y) else "x")
    print("y=%6.1f " % y + "".join(row))
