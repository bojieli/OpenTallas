"""DIE-QC-22: snake wire OUTSIDE the DME regions (spine/feed ladder legs) by side and by y band; routed per-leg delay vs
straight length.  usage: feedsnake.py TOOLS TRIAL ARR_PREFIX"""
import json, sys
from collections import defaultdict
sys.path.insert(0, sys.argv[1]); import die_trial as D
K, A = sys.argv[2:4]
T = json.load(open(f"{K}/clock/tree.json"))
nodes = {int(k): v for k, v in T["nodes"].items()}
nb = {int(k): v for k, v in T["node_buf"].items()}
arr = {}
for ln in open(f"{A}_TT/arr_TT.txt"):
    p = ln.split()
    if p[0] == "N": arr[p[1]] = float(p[2])
agg = defaultdict(lambda: [0, 0.0, 0.0, 0.0])
top = []
keys = set()
for i, nd in nodes.items():
    if nd.get("dme") or nd.get("parent") is None: continue
    keys.update(nd.keys())
    p = nodes[nd["parent"]]
    pts = [(p["x"], p["y"])] + [tuple(x) for x in (nd.get("snake") or nd.get("route") or [])] + [(nd["x"], nd["y"])]
    L = sum(D._man(u, v) for u, v in zip(pts, pts[1:])); S = D._man(pts[0], pts[-1])
    x = nd["x"] / 1000; y = nd["y"] / 1000
    side = "west" if 2.0 <= x <= 13.5 else "east" if x > 13.5 else "other"
    band = "glue_row_y10-11" if 10.0 <= y <= 11.0 else "rest"
    a = agg[(side, band)]; a[0] += 1; a[1] += L; a[2] += L - S
    ca, pa = arr.get(nb.get(i)), arr.get(nb.get(nd["parent"]))
    if L - S > 300:
        top.append((round(L - S), side, band, i, round(x, 2), round(y, 2), nd.get("feed_edge") or nd.get("kind"),
                    None if ca is None or pa is None else round(ca - pa, 1), round(S)))
print("node keys", sorted(keys))
for k, v in sorted(agg.items()): print(k, "legs", v[0], "wire_um", round(v[1]), "extra(snake/detour)_um", round(v[2]))
top.sort(reverse=True)
print("legs with >300 um extra (top 25): extra, side, band, node, x, y, feed_edge, routed ps, straight um")
for t in top[:25]: print(t)
print("count west", sum(1 for t in top if t[1] == "west"), "east", sum(1 for t in top if t[1] == "east"),
      "extra_um west", sum(t[0] for t in top if t[1] == "west"), "east", sum(t[0] for t in top if t[1] == "east"))
