"""DIE-QC-23: routed vs model delay of every trial14 snake leg, binned by snake leg length (TT, stage-cal model).
usage: snake_len23.py TOOLS TRIAL ARR_TT CAL OUT.json"""
import json, sys, statistics as st
sys.path.insert(0, sys.argv[1]); import die_trial as D
K, A, CAL, OUT = sys.argv[2:6]
D.EVEN_LEGS = True; D.load_stage_cal(CAL)
T = json.load(open(f"{K}/clock/tree.json"))
n = {int(k): v for k, v in T["nodes"].items()}
nb = {int(k): v for k, v in T["node_buf"].items()}
arr = {}
for ln in open(A):
    p = ln.split()
    if p[0] == "N": arr[p[1]] = float(p[2])
rows = []
for k, v in n.items():
    if not v.get("snake") or v.get("parent") is None: continue
    p = n[v["parent"]]
    pts = [(p["x"], p["y"])] + [tuple(x) for x in v["snake"]] + [(v["x"], v["y"])]
    L = sum(D._man(a, b) for a, b in zip(pts, pts[1:]))
    m = D.chain_ps(pts) + D.DME_FANOUT_PS * (max(1, len(v.get("kids", []))) - 1)
    ca, pa = arr.get(nb.get(k)), arr.get(nb.get(v["parent"]))
    if ca is None or pa is None: continue
    rows.append(dict(node=k, L=round(L, 1), span=round(D._man(pts[0], pts[-1]), 1), bufs=len(v["snake"]), model=round(m, 1),
                     routed=round(ca - pa, 1), ratio=round((ca - pa) / m, 3), maxseg=round(max(D._man(a, b) for a, b in zip(pts, pts[1:])), 1)))
bins = [(0, 400), (400, 800), (800, 1200), (1200, 1600), (1600, 9e9)]
summ = []
for lo, hi in bins:
    s = [r for r in rows if lo <= r["L"] < hi]
    if s:
        summ.append(dict(L=f"{lo}-{hi}", n=len(s), ratio_med=round(st.median(r["ratio"] for r in s), 3),
                         err_med_ps=round(st.median(r["routed"] - r["model"] for r in s), 1),
                         err_max_ps=round(max(r["routed"] - r["model"] for r in s), 1)))
json.dump(dict(summary=summ, rows=rows), open(OUT, "w"), indent=0)
for s in summ: print(s)
rows.sort(key=lambda r: -(r["routed"] - r["model"]))
for r in rows[:8]: print(r)
