"""DIE-QC-24: root-cause repeater slides: planned (pre-legal) repeater point vs placed, which leg branch, why illegal,
and whether a legal point exists ON the planned leg within +-rep/2 of arc length.
usage: slide24.py TOOLS_DIE_PLAN PLAN TRIAL [REP_UM]"""
import sys, json, re, collections, math
sys.path.insert(0, sys.argv[1])
import die_trial as D, schema as S
from pathlib import Path
P = S.Plan(S.load(sys.argv[2]), Path(sys.argv[2])); K = sys.argv[3]; rep = float(sys.argv[4]) if len(sys.argv) > 4 else 250.0
site = D.SiteMap(P)
T = json.load(open(f"{K}/clock/tree.json")); N = {int(k): v for k, v in T["nodes"].items()}
pl = {}
for l in open(f"{K}/clock/ctree.tcl"):
    m = re.match(r"place_inst -name r(\d+)_(\d+) -location \{([\d.]+) ([\d.]+)\}", l)
    if m: pl[(int(m.group(1)), int(m.group(2)))] = (float(m.group(3)), float(m.group(4)))
def dseg(p, a, b):
    (x, y), (x0, y0), (x1, y1) = p, a, b
    cx = min(max(x, min(x0, x1)), max(x0, x1)); cy = min(max(y, min(y0, y1)), max(y0, y1)); return abs(x - cx) + abs(y - cy)
out = []; br = collections.Counter(); onleg = collections.Counter()
for (i, j), c in pl.items():
    nd = N[i]; p = N[nd["parent"]]
    if nd.get("snake"): kind = "snake"; poly = [(p["x"], p["y"])] + [tuple(q) for q in nd["snake"]] + [(nd["x"], nd["y"])]
    elif nd.get("detour"): kind = "route/detour"; poly = [tuple(q) for q in nd["detour"]]
    else: kind = "straight"; poly = [(p["x"], p["y"]), (nd["x"], nd["y"])]
    d = min(dseg(c, a, b) for a, b in zip(poly, poly[1:]))
    if d <= 50: continue
    n = sum(1 for (a, b) in pl if a == i)
    _, L = D.polyline_points(poly, [])
    f = (j + 1) / (n + 1); q, _ = D.polyline_points(poly, [f])
    q = q[0]; why = site.why(q); hit = site.hits(q)
    # legal on-leg point within +-rep/2 arc
    best = None
    for s in range(1, int(rep / 2 / 0.54) + 1):
        for sg in (1, -1):
            ff = f + sg * s * 0.54 / L
            if 0 < ff < 1:
                qq, _ = D.polyline_points(poly, [ff]); qq = qq[0]
                if site.legal(qq): best = s * 0.54; break
        if best: break
    br[kind] += 1; onleg["found" if best else "none"] += 1
    out.append(dict(node=i, rep=j, kind=kind, region=nd.get("dme"), off_um=round(d, 1), planned=[round(v, 2) for v in q],
                    placed=c, why=why, hit=[round(v, 1) for v in hit[0][:4]] if hit else None,
                    hit_wh=[round(hit[0][2]-hit[0][0], 1), round(hit[0][3]-hit[0][1], 1)] if hit else None,
                    onleg_slide_um=best, leg_um=round(L, 1), nrep=n))
print(json.dumps(dict(trial=K, slid_gt50=len(out), branch=br, onleg=onleg,
                      worst=sorted(out, key=lambda r: -r["off_um"])[:6]), indent=1))
