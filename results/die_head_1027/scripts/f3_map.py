# DIE-HEAD: re-derive the LAND-HEAD-3 27-region link_forward region map (experimental build_link_forward, cap 1.3 ns)
import json, sys
from pathlib import Path
W = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(W / "tools/die_plan")); sys.path.insert(0, str(W / "results/land_head_3_1027/experimental"))
import die_trial as D, experimental_link_forms as X
import math, collections
from collections import defaultdict
for k in ("math","collections","defaultdict"): setattr(X, k, globals()[k])
for k in dir(D):
    if not hasattr(X, k): setattr(X, k, getattr(D, k))
S = D.S
P = S.Plan(S.load(sys.argv[1]), Path(sys.argv[1]))
taps = D.clock_taps(P)
nodes = X.build_link_forward(P, taps)
reg = {}
for n in nodes.values():
    if n.get("part") and n.get("clock_region") not in (None, "top"):
        reg[n["part"]] = n["clock_region"]
rs = sorted(set(reg.values()), key=lambda r: (-sum(1 for v in reg.values() if v == r), str(r)))
nm = {r: f"R{i:02d}" for i, r in enumerate(rs)}
out = dict(source="LAND-HEAD-3 build_link_forward (cap 1300 ps, near 1100 um) re-derived by DIE-HEAD", plan=sys.argv[1],
           part_region={p: nm[r] for p, r in sorted(reg.items())}, link_dme=nodes[0].get("link_dme"))
Path(sys.argv[2]).write_text(json.dumps(out, indent=1) + "\n")
print(len(reg), len(rs), nodes[0].get("link_dme"))
