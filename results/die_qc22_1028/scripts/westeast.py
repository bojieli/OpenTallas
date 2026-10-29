"""DIE-QC-22 (COORD spot-check): ROUTED glue-tap spread per DME region, west (x 2-13.5 mm) vs east, + snake wire and
region-root (feed) arrival per region.  usage: westeast.py TOOLS TRIAL ARR_PREFIX OUT.json"""
import json, sys, statistics as st
from collections import defaultdict
sys.path.insert(0, sys.argv[1]); import die_trial as D
K, A, OUT = sys.argv[2:5]
T = json.load(open(f"{K}/clock/tree.json"))
nodes = {int(k): v for k, v in T["nodes"].items()}
nb = {int(k): v for k, v in T["node_buf"].items()}
arr = {}
for C in ("TT", "FF"):
    a = {}
    for ln in open(f"{A}_{C}/arr_{C}.txt"):
        p = ln.split()
        if p[0] == "N": a[p[1]] = float(p[2])
        elif p[0] == "T": a["port:" + p[1]] = float(p[2])
    arr[C] = a
reg = defaultdict(lambda: dict(snake_um=0.0, snake_legs=0, legs=0, wire_um=0.0, root=None, taps={"TT": [], "FF": []}, xs=[]))
for i, nd in nodes.items():
    rn = nd.get("dme")
    if not rn or nd.get("parent") is None: continue
    r = reg[rn]; p = nodes[nd["parent"]]
    pts = [(p["x"], p["y"])] + [tuple(x) for x in (nd.get("snake") or nd.get("route") or [])] + [(nd["x"], nd["y"])]
    L = sum(D._man(u, v) for u, v in zip(pts, pts[1:]))
    r["legs"] += 1; r["wire_um"] += L
    if nd.get("snake"):
        r["snake_legs"] += 1; r["snake_um"] += L - D._man(pts[0], pts[-1])
    if p.get("dme") != rn:          # region root leg: parent outside the region = the feed
        r["root"] = i
for t in T["taps"]:
    port = t["port"]; tap = port.rsplit("__", 1)[1]
    n = t.get("node")
    rn = nodes.get(n, {}).get("dme") if n is not None else None
    if not rn or tap.startswith("clk_c"): continue
    for C in ("TT", "FF"):
        v = arr[C].get("port:" + port)
        if v is not None: reg[rn]["taps"][C].append(v)
    reg[rn]["xs"].append(t["xy"][0])
rows = []
for rn, r in reg.items():
    if len(r["taps"]["TT"]) < 2: continue
    x = st.mean(r["xs"]) / 1000.0
    ra = {C: arr[C].get(nb.get(r["root"])) for C in ("TT", "FF")} if r["root"] is not None else {}
    rows.append(dict(region=rn, x_mm=round(x, 2), side="west" if 2.0 <= x <= 13.5 else "east" if x > 13.5 else "other",
                     spread_TT=round(max(r["taps"]["TT"]) - min(r["taps"]["TT"]), 1),
                     spread_FF=round(max(r["taps"]["FF"]) - min(r["taps"]["FF"]), 1),
                     glue_med_TT=round(st.median(r["taps"]["TT"]), 1), root_TT=ra.get("TT") and round(ra["TT"], 1),
                     snake_um=round(r["snake_um"]), snake_legs=r["snake_legs"], legs=r["legs"], wire_um=round(r["wire_um"])))
summ = {}
for side in ("west", "east", "other"):
    rs = [r for r in rows if r["side"] == side]
    if not rs: continue
    def q(k, f=0.5):
        v = sorted(r[k] for r in rs); return v[min(len(v) - 1, int(f * len(v)))]
    rsn = [r for r in rs if r["root_TT"] is not None]
    summ[side] = dict(regions=len(rs), spread_TT_med=q("spread_TT"), spread_TT_p90=q("spread_TT", .9),
                      spread_TT_max=max(r["spread_TT"] for r in rs), spread_FF_med=q("spread_FF"),
                      spread_FF_max=max(r["spread_FF"] for r in rs), snake_um_sum=sum(r["snake_um"] for r in rs),
                      snake_um_med=q("snake_um"), wire_um_sum=sum(r["wire_um"] for r in rs),
                      snake_share=round(sum(r["snake_um"] for r in rs) / max(1, sum(r["wire_um"] for r in rs)), 3),
                      root_TT_min=min((r["root_TT"] for r in rsn), default=None),
                      root_TT_max=max((r["root_TT"] for r in rsn), default=None),
                      glue_med_TT_range=[min(r["glue_med_TT"] for r in rs), max(r["glue_med_TT"] for r in rs)])
json.dump(dict(summary=summ, rows=sorted(rows, key=lambda r: r["x_mm"])), open(OUT, "w"), indent=0)
print(json.dumps(summ, indent=1))
# correlation snake vs spread
import math
xs = [r["snake_um"] for r in rows]; ys = [r["spread_TT"] for r in rows]
mx, my = st.mean(xs), st.mean(ys)
c = sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / math.sqrt(sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys))
print("corr(snake_um, spread_TT) over regions", round(c, 3))
for r in sorted(rows, key=lambda r: -r["spread_TT"])[:8]: print(r)
