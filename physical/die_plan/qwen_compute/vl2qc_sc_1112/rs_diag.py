"""VL2QC-SC: which nets load a route_supply hot bin (V): run route_supply.main with record_nets for one type, then sum
the recorded net bits whose bbox spans the probe point vertically (x within [x0-d, x1+d], y inside [y0, y1]).
usage: rs_diag.py TOOLS PLAN TYPE X Y [D]"""
import sys, collections
tools, plan, tn, X, Y = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]), float(sys.argv[5])
D = float(sys.argv[6]) if len(sys.argv) > 6 else 6.0
MODE = sys.argv[7] if len(sys.argv) > 7 else "V"
sys.path.insert(0, tools + "/tools/die_plan"); sys.path.insert(0, tools)
import route_supply as R
orig = R.analyze_type
recs = {}
def wrap(name, t, die_dir, repo, conns, cfg):
    if name == tn:
        cfg = dict(cfg, record_nets=True)
    r = orig(name, t, die_dir, repo, conns, cfg)
    if name == tn:
        recs["rec"] = r.get("_rec") if isinstance(r, dict) else None
    return r
R.analyze_type = wrap
import os
os.chdir(tools)
try:
    R.main([plan, "--die", "qwen_compute", "--repo", ".", "--match", "^" + tn + "$", "--grt-halving", "edge_outline", "--out", "/tmp/rsdiag_" + str(os.getpid())])
except SystemExit:
    pass
rec = recs.get("rec") or []
acc = collections.Counter(); accH = collections.Counter()
for cat, label, x0, x1, y0, y1, n in rec:
    if MODE == "V" and x0 - D <= X <= x1 + D and y0 <= Y <= y1 and (y1 - y0) > 1:
        acc[(cat, str(label)[:70])] += n
    if MODE == "H" and y0 - D <= Y <= y1 + D and x0 <= X <= x1 and (x1 - x0) > 1:
        acc[(cat, str(label)[:70])] += n
print("recorded", len(rec), "V-crossing nets at", X, Y)
for k, v in acc.most_common(25):
    print(f"{v:7.0f}  {k[0]:8s} {k[1]}")
