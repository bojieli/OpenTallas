"""DIE-QC-23: per-leg routed residual vs the fixed calibrated model (val14 coef), by leg class.
usage: legres23.py TOOLS VAL14 TRIAL ARRPFX [TRIAL ARRPFX ...]"""
import json, sys, math, re, statistics as st, collections
import numpy as np
sys.path.insert(0, sys.argv[1]); import die_trial as D
v = json.load(open(sys.argv[2])); coef = np.array(v["leg_coef"]["TT"])
args = sys.argv[3:]
for K, A in zip(args[::2], args[1::2]):
    T = json.load(open(f"{K}/clock/tree.json")); N = {int(k): x for k, x in T["nodes"].items()}
    nb = {int(k): x for k, x in T["node_buf"].items()}; nt = collections.defaultdict(int)
    for t in T["taps"]: nt[t["node"]] += 1
    a = {}
    for l in open(f"{A}_TT/arr_TT.txt"):
        p = l.split()
        if p[0] == "N": a[p[1]] = float(p[2])
    pl = collections.defaultdict(list)
    for l in open(f"{K}/clock/ctree.tcl"):
        m = re.match(r"place_inst -name r(\d+)_(\d+) -location \{([\d.]+) ([\d.]+)\}", l)
        if m: pl[int(m.group(1))].append((float(m.group(3)), float(m.group(4))))
    rows = []
    for i, nd in N.items():
        if not nd.get("dme") or nd.get("parent") is None or N[nd["parent"]].get("dme") != nd["dme"]: continue
        if nb.get(i) not in a or nb.get(nd["parent"]) not in a: continue
        p = N[nd["parent"]]
        if nd.get("snake"):
            pts = [(p["x"], p["y"])] + [tuple(x) for x in nd["snake"]] + [(nd["x"], nd["y"])]; s = [D._man(x, y) for x, y in zip(pts, pts[1:])]
        else:
            pts = [tuple(x) for x in nd["route"]] if nd.get("route") else [(p["x"], p["y"]), (nd["x"], nd["y"])]
            L = sum(D._man(x, y) for x, y in zip(pts, pts[1:])); n = max(1, math.ceil(L / 250 - 1e-9)); n += n % 2; s = [L / n] * n
        m = float(coef @ [len(s), sum(s), sum(x * x for x in s), len(nd["kids"]) + nt[i] - 1])
        r = a[nb[i]] - a[nb[nd["parent"]]]
        cells = [(p["x"], p["y"])] + sorted(pl.get(i, []), key=lambda c: D._man(c, (p["x"], p["y"])))
        hop = max(D._man(x, y) for x, y in zip(cells, cells[1:])) if len(cells) > 1 else 0
        cls = "snake" if nd.get("snake") else ("long" if sum(s) > 400 else "short")
        rows.append(dict(i=i, rn=nd["dme"], cls=cls, L=sum(s), res=r - m, maxhop=hop))
    print(K, "legs", len(rows))
    for c in ("short", "long", "snake"):
        R = [x["res"] for x in rows if x["cls"] == c]
        if R: print(f"  {c:6s} n {len(R):5d} res med {st.median(R):6.1f} sd {st.pstdev(R):5.1f} max|.| {max(abs(x) for x in R):6.1f} >30 {sum(abs(x) > 30 for x in R)}")
    H = [x for x in rows if x["maxhop"] > 300]
    print("  legs with a cell hop >300um", len(H), "res med", round(st.median(x["res"] for x in H), 1) if H else None)
    print("  worst", [(x["i"], x["rn"], x["cls"], round(x["L"]), round(x["res"], 1), round(x["maxhop"])) for x in sorted(rows, key=lambda x: -abs(x["res"]))[:5]])
