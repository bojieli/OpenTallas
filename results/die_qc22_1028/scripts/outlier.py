"""DIE-QC-22: per-leg routed vs model on the late vs early glue tap paths of one DME region (c_W2_bn_01 outlier).
usage: outlier.py TOOLS TRIAL ARR_PREFIX REGION TAP_LATE TAP_EARLY"""
import json, sys
sys.path.insert(0, sys.argv[1]); import die_trial as D
K, A, RG, TL, TE = sys.argv[2:7]
T = json.load(open(f"{K}/clock/tree.json"))
nodes = {int(k): v for k, v in T["nodes"].items()}
nb = {int(k): v for k, v in T["node_buf"].items()}
D.EVEN_LEGS = True
arr = {}
for ln in open(f"{A}_TT/arr_TT.txt"):
    p = ln.split()
    if p[0] == "N": arr[p[1]] = float(p[2])
    elif p[0] == "T": arr["port:" + p[1]] = float(p[2])
taps = T["taps"]
print(type(taps), (list(taps.items())[:1] if isinstance(taps, dict) else taps[:1]))
def tap_node(port):
    if isinstance(taps, dict):
        v = taps.get(port); return v if isinstance(v, int) else (v or {}).get("node")
    for t in taps:
        if t.get("port") == port: return t.get("node")
rep = T["meta"].get("rep_um", 250.0)
def path(n):
    out = []
    while n is not None:
        out.append(n); n = nodes[n].get("parent")
    return out
pl, pe = path(tap_node(f"t_{RG}__{TL}")), path(tap_node(f"t_{RG}__{TE}"))
common = next(n for n in pl if n in set(pe))
print("common", common, nodes[common].get("dme"), "arr", arr.get(nb.get(common)))
for name, pth in (("late", pl), ("early", pe)):
    tot_m = tot_r = 0
    for n in pth[:pth.index(common)][::-1]:
        nd = nodes[n]; p = nodes[nd["parent"]]
        pts = [(p["x"], p["y"])] + [tuple(x) for x in (nd.get("snake") or nd.get("route") or [])] + [(nd["x"], nd["y"])]
        L = sum(D._man(a, b) for a, b in zip(pts, pts[1:]))
        m = D.chain_ps(pts) if nd.get("snake") else D.leg_ps(L, rep)
        ca, pa = arr.get(nb.get(n)), arr.get(nb.get(nd["parent"]))
        r = None if ca is None or pa is None else ca - pa
        tot_m += m; tot_r += (r or 0)
        print(name, n, "L", round(L, 1), "snake" if nd.get("snake") else "", "kids", len(nd.get("kids", [])), "model", round(m, 1),
              "routed", None if r is None else round(r, 1), "xy", (round(nd["x"], 1), round(nd["y"], 1)))
    print(name, "SUM model", round(tot_m, 1), "routed", round(tot_r, 1))
