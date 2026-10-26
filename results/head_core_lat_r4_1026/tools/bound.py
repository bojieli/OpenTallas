"""equal-path-length lower bound: leaf TT-rise / FF-early vs root->leaf wire path; fit + value at the max path."""
import sys, json
sys.path.insert(0, "py"); import common
S = common.parse_spec(sys.argv[1]); seg = json.load(open(sys.argv[2]))["seg_um"]; P = json.load(open(sys.argv[3]))
par = {n: v["par"] for n, v in S["tree"].items()}; par.update({n: v["par"] for n, v in S["leaves"].items()})
def L(n):
    s = 0
    while n != "root": s += seg.get(n, 0); n = par[n]
    return s
xs = [L(n) for n in S["leaves"]]
o = {}
for k, C, b in (("TT", "TT_leaf", "rise"), ("FFe", "FF_leaf", "early")):
    ys = [P[C][n][b] for n in S["leaves"]]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sl = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    o[k] = dict(slope_ps_per_um=round(sl, 4), at_max_path=round(my + sl * (max(xs) - mx), 1), max_leaf=round(max(ys), 1), mean=round(my, 1))
o["path_um"] = [round(min(xs), 1), round(max(xs), 1)]
print(json.dumps(o))
