#!/usr/bin/env python3
"""R18: per-net model-vs-RCX stage comparison on the R17 explicit clock build.
usage: r18_netcmp.py TREE_DIR STAGE_TABLE CORNER OUT_JSON
TREE_DIR has nets.json, place.json, rcx.spef, r17_tree_<C>_rcx.txt (N lines: cell Yarr_max Yarr_min Yslew Aarr_max Aslew).
Model stage = Stage.seg(w, m, C, L) with L = Manhattan driver-site -> load-site (as qc_clk_mesh3 phys_edges)."""
import json, sys, re, math, collections
import numpy as np

tree, stage_p, C, out = sys.argv[1:5]
N = json.load(open(f"{tree}/nets.json"))["nets"]
P = json.load(open(f"{tree}/place.json"))
arr = {}
for ln in open(f"{tree}/r17_tree_{C}_rcx.txt"):
    f = ln.split()
    if f[0] == "N":
        arr[f[1]] = dict(y=float(f[2]), a=float(f[5]), sa=float(f[6]), sy=float(f[4]))
    elif f[0] == "T" and f[2] != "NA":
        arr[f[1]] = dict(a=float(f[2]), sa=float(f[4]))
# spef: per net total C (pF) and name map
nm, capt, curnet = {}, {}, None
sec = None
for ln in open(f"{tree}/rcx.spef"):
    if ln.startswith("*NAME_MAP"):
        sec = "nm"; continue
    if sec == "nm":
        m = re.match(r"\*(\d+) (\S+)", ln)
        if m:
            nm["*" + m.group(1)] = m.group(2); continue
        elif ln.strip() == "":
            continue
        else:
            sec = None
    if ln.startswith("*D_NET"):
        _, n, c = ln.split()[:3]
        capt[nm.get(n, n)] = float(c) * 1000.0
# stage fit (same as qc_clk_mesh3.Stage)
T = json.load(open(stage_p))
D0 = {"TT": 34.0, "FF": 27.2}
fit = {}
for key in {(r["w"], r["mult"], r["corner"]) for r in T["rows"] if "error" not in r}:
    rr = sorted((r for r in T["rows"] if "error" not in r and (r["w"], r["mult"], r["corner"]) == key), key=lambda r: r["L"])
    L = np.array([r["L"] for r in rr], float); D = np.array([r["stage_ps"] for r in rr], float)
    fit[key] = np.polyfit(np.concatenate([[0.0], L]), np.concatenate([[D0[key[2]]], D]), 2)
rc = T["rc"]
rows = []
for n in N:
    if n["drv"].startswith("port:"):
        continue
    d = n["drv"]; units = len(n.get("drv_units", [d]))
    dp = P[d]
    for ld in n["loads"]:
        if ld.startswith("port:") or ld.startswith("t_"):
            continue
        if ld not in P or ld not in arr or d not in arr:
            continue
        L = abs(P[ld]["x"] - dp["x"]) + abs(P[ld]["y"] - dp["y"])
        rows.append(dict(net=n["name"], drv=d, load=ld, units=units, L=L, nloads=len(n["loads"]),
                         rcx=arr[ld]["a"] - arr[d]["a"], cap=capt.get(n["name"], float("nan")),
                         layers=n.get("plan_layers"), kind=P[d].get("plan_kind")))
    # tap ports
for r in rows:
    m = 2 if r["units"] >= 2 else 1
    r["model"] = float(np.polyval(fit[("16w", m, C)], r["L"]))
rows_u = {}
for r in rows:                         # one row per net (worst load)
    k = r["net"]
    if k not in rows_u or r["rcx"] > rows_u[k]["rcx"]:
        rows_u[k] = r
R = list(rows_u.values())
L = np.array([r["L"] for r in R]); rcx = np.array([r["rcx"] for r in R]); mod = np.array([r["model"] for r in R])
cap = np.array([r["cap"] for r in R])
ok = np.isfinite(cap)
# cap per um of routed tree wire vs model c_fF_um (Manhattan legs; loads per net summed: use sum of L over loads/net as a proxy)
Lsum = collections.defaultdict(float)
for r in rows:
    Lsum[r["net"]] += r["L"]
cpu = np.array([capt[k] / Lsum[k] for k in rows_u if Lsum[k] > 50 and k in capt])
hist = collections.Counter(r["units"] for r in R)
res = dict(corner=C, nets=len(R), units_hist=dict(hist),
           L_um=dict(min=float(L.min()), med=float(np.median(L)), max=float(L.max())),
           rcx_stage_ps=dict(min=float(rcx.min()), med=float(np.median(rcx)), max=float(rcx.max()), sum=float(rcx.sum())),
           model_stage_ps=dict(min=float(mod.min()), med=float(np.median(mod)), max=float(mod.max()), sum=float(mod.sum())),
           ratio_med=float(np.median(mod / np.maximum(rcx, 1e-3))),
           rcx_cap_fF_per_um_med=float(np.median(cpu)) if len(cpu) else None,
           model_c_fF_um_16w=rc["16w"][1], model_r_ohm_um_16w=rc["16w"][0],
           by_L=[])
for lo, hi in [(0, 50), (50, 150), (150, 300), (300, 450), (450, 2000)]:
    s = (L >= lo) & (L < hi)
    if s.any():
        res["by_L"].append(dict(L=[lo, hi], n=int(s.sum()), rcx_med=float(np.median(rcx[s])), model_med=float(np.median(mod[s])),
                                cap_med_fF=float(np.nanmedian(cap[s]))))
# least squares rcx = a + b L
A = np.vstack([np.ones_like(L), L]).T
co, *_ = np.linalg.lstsq(A, rcx, rcond=None)
res["rcx_fit_ps"] = dict(intercept=float(co[0]), per_um=float(co[1]))
co2, *_ = np.linalg.lstsq(A, mod, rcond=None)
res["model_fit_ps"] = dict(intercept=float(co2[0]), per_um=float(co2[1]))
json.dump(dict(summary=res, rows=R), open(out, "w"), indent=0)
print(json.dumps(res, indent=1))
