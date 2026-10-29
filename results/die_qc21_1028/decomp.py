"""DIE-QC-21: per DME region, model vs routed arrival of A0 (early core) taps vs glue taps, from the region DME root.
usage: decomp.py TOOLS_DIR TRIAL_DIR ARR_PREFIX PLAN PART_REGION OUT.json"""
import json, sys, statistics as st
from collections import defaultdict
sys.path.insert(0, sys.argv[1])
import die_trial as D, schema as S
K, A, PL, PR, OUT = sys.argv[2:7]
D.EVEN_LEGS = True
P = S.Plan(json.load(open(PL)))
T = json.load(open(f"{K}/clock/tree.json"))
nodes = {int(k): v for k, v in T["nodes"].items()}
nb = {int(k): v for k, v in T["node_buf"].items()}
reg = json.load(open(PR))["part_region"]
contracts = {(p, n): tp for p, pp in P.parts.items() for n, _, _, tp in S.core_taps(P, pp["type"])}
rep = T["meta"].get("rep_um", 250.0)
arr = {}
for C in ("TT", "FF"):
    a = {}
    for ln in open(f"{A}_{C}/arr_{C}.txt"):
        p = ln.split()
        if p[0] == "N": a[p[1]] = float(p[2])
        elif p[0] == "T": a["port:" + p[1]] = float(p[2])
    arr[C] = a

def leg_model(i):
    nd = nodes[i]; p = nodes[nd["parent"]]
    pa, q = (p["x"], p["y"]), (nd["x"], nd["y"])
    if nd.get("snake"):
        return D.chain_ps([pa] + [tuple(x) for x in nd["snake"]] + [q]), "snake"
    pts = [tuple(x) for x in nd["route"]] if nd.get("route") else [pa, q]
    return D.leg_ps(sum(D._man(a, b) for a, b in zip(pts, pts[1:])), rep), "plain"

def droot(i):
    rn = nodes[i].get("dme")
    while nodes[i].get("parent") is not None and nodes[nodes[i]["parent"]].get("dme") == rn:
        i = nodes[i]["parent"]
    return i

rows = defaultdict(lambda: dict(core=[], glue=[]))
for t in T["taps"]:
    n = t["node"]; rn = nodes[n].get("dme")
    if not rn: continue
    r0 = droot(n)
    mp, i, sn = 0.0, n, 0.0
    while i != r0:
        m, c = leg_model(i); mp += m
        if c == "snake": sn += m
        i = nodes[i]["parent"]
    tw = D.tap_wire_ps(D._man((nodes[n]["x"], nodes[n]["y"]), tuple(t["xy"])))
    tp = contracts.get((t["part"], t["tap"]))
    rec = dict(port=t["port"], model=mp + tw, model_tapwire=tw, model_snake=sn)
    for C in ("TT", "FF"):
        rec[C] = arr[C]["port:" + t["port"]] - arr[C][nb[r0]]
        if tp: rec["early_" + C] = S.core_tap_early_ps(P, tp, C)
    rows[rn]["core" if tp else "glue"].append(rec)
res = {}
for rn, d in rows.items():
    if not d["core"] or not d["glue"]: continue
    m = lambda L, k: st.mean(x[k] for x in L)
    r = dict(n_core=len(d["core"]), n_glue=len(d["glue"]),
             model_glue_minus_core=round(m(d["glue"], "model") - m(d["core"], "model"), 2),
             glue_snake_model=round(m(d["glue"], "model_snake"), 1), core_snake_model=round(m(d["core"], "model_snake"), 1),
             core_model=round(m(d["core"], "model"), 1), glue_model=round(m(d["glue"], "model"), 1))
    for C in ("TT", "FF"):
        r[f"routed_glue_minus_core_{C}"] = round(m(d["glue"], C) - m(d["core"], C), 2)
        r[f"early_{C}"] = round(m(d["core"], "early_" + C), 2)
        r[f"core_{C}"] = round(m(d["core"], C), 1); r[f"glue_{C}"] = round(m(d["glue"], C), 1)
    res[rn] = r
summ = {}
for k in ("c_", "su_c"):
    L = [v for n, v in res.items() if (n.startswith("c_") if k == "c_" else "su_c" in n)]
    if not L: continue
    s = dict(regions=len(L))
    for f in ("model_glue_minus_core", "routed_glue_minus_core_TT", "routed_glue_minus_core_FF", "early_TT", "early_FF",
              "core_model", "glue_model", "core_TT", "glue_TT", "core_FF", "glue_FF", "glue_snake_model", "core_snake_model"):
        s[f] = round(st.median(x[f] for x in L), 2)
    s["realized_ratio_TT"] = round(s["routed_glue_minus_core_TT"] / s["model_glue_minus_core"], 4)
    s["realized_ratio_FF"] = round(s["routed_glue_minus_core_FF"] / s["model_glue_minus_core"], 4)
    s["core_ratio_TT"] = round(s["core_TT"] / s["core_model"], 4); s["glue_ratio_TT"] = round(s["glue_TT"] / s["glue_model"], 4)
    s["core_ratio_FF"] = round(s["core_FF"] / s["core_model"], 4); s["glue_ratio_FF"] = round(s["glue_FF"] / s["glue_model"], 4)
    summ[k] = s
json.dump(dict(summary=summ, regions=res), open(OUT, "w"), indent=0)
print(json.dumps(summ, indent=1))
