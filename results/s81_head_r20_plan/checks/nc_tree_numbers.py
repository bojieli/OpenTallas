"""Independent NUMBER-CHECK of HEAD R19 tree numbers. Own code: no import of head_mesh_r3/qc_clk_mesh3/master_plan.
Legs recomputed from node xy (Manhattan), nseg=ceil(L/450), stage delay = own fit of the ngspice stage table rows."""
import json, math, sys
import numpy as np
T, stab = sys.argv[1], sys.argv[2]
nodes = json.load(open(f"{T}/tree_nodes.json")); by = {n["tag"]: n for n in nodes}
st = json.load(open(stab)); rows = [r for r in st["rows"] if "error" not in r]
D0 = {"TT": 34.0, "FF": 27.2}
def fit(w, m, c, anchor=True, deg=2):
    rr = sorted([r for r in rows if r["w"] == w and r["mult"] == m and r["corner"] == c], key=lambda r: r["L"])
    L = [r["L"] for r in rr]; D = [r["stage_ps"] for r in rr]
    if anchor: L, D = [0.0] + L, [D0[c]] + D
    return np.polyfit(L, D, min(deg, len(L) - 1)), rr
def seg(cf, L): return float(np.polyval(cf, L))
roots = [n for n in nodes if not n.get("parent")]; assert len(roots) == 1, len(roots)
leaves = [n for n in nodes if not n["kids"]]
# consistency: kids <-> parent
for n in nodes:
    for k in n["kids"]: assert by[k]["parent"] == n["tag"]
def path(n):
    p = []
    while n.get("parent"): p.append(n); n = by[n["parent"]]
    return p
res = {}
mism = 0
for c in ("TT", "FF"):
    cf, rr = fit("16w", 2, c)
    print(c, "16w m2 table rows", [(r["L"], r["stage_ps"]) for r in rr], "fit", [round(x, 6) for x in cf])
    arr, stg, plen = [], [], []
    for lf in leaves:
        t = s = pl = 0.0
        for e in path(lf):
            px = by[e["parent"]]["xy"]; L = abs(px[0] - e["xy"][0]) + abs(px[1] - e["xy"][1])
            if abs(L - e["leg"]) > 1e-3: mism += 1
            n = max(1, math.ceil(L / 450 - 1e-9)) if L > 1e-9 else 1
            t += n * seg(cf, L / n); s += n; pl += L
        arr.append(t); stg.append(s); plen.append(pl)
    res[c] = dict(min=min(arr), max=max(arr), stages=sorted(set(stg)), path=(min(plen), max(plen)))
    # sensitivity: piecewise-linear through table points (no quadratic)
    Ls = [0.0] + [r["L"] for r in rr]; Ds = [D0[c]] + [r["stage_ps"] for r in rr]
    lin = []
    for lf in leaves:
        t = 0.0
        for e in path(lf):
            px = by[e["parent"]]["xy"]; L = abs(px[0] - e["xy"][0]) + abs(px[1] - e["xy"][1])
            n = max(1, math.ceil(L / 450 - 1e-9)) if L > 1e-9 else 1
            t += n * float(np.interp(L / n, Ls, Ds))
        lin.append(t)
    res[c]["linear_interp"] = (min(lin), max(lin))
print("leaves", len(leaves), "nodes", len(nodes), "leg mismatches vs stored", mism)
for c, v in res.items(): print(c, {k: (tuple(round(x, 2) for x in v[k]) if isinstance(v[k], tuple) else (round(v[k], 2) if isinstance(v[k], float) else v[k])) for k in v})
# repeaters
rep = sum(max(1, math.ceil(n["leg"] / 450 - 1e-9)) - 1 for n in nodes if n.get("parent"))
wire = sum(n["leg"] for n in nodes if n.get("parent"))
print("repeaters", rep, "wire_um", round(wire, 2))
# pair skew: own pitch from straps (mean adjacent gap, per layer), QC b3 constants from their raw measured ratios
S = json.load(open(f"{T}/straps.json"))
M = json.load(open(f"{T}/mesh.json"))["meta"]
print("mesh meta pitch_um", M.get("pitch_um"), "trunk_um", M.get("trunk_um"), "regions_depth", M.get("regions_depth"))
for lay in ("M8", "M9"):
    xs = sorted(set(round(s[1], 3) for s in S if s[0] == lay)); g = np.diff(xs)
    print(lay, "n", len(xs), "gap mean %.2f median %.2f max %.2f" % (g.mean(), np.median(g), g.max()))
Lp = max(res["TT"]["path"])
for c, (sp, ocv_n, ocv_d, ins_qc) in {"TT": (103.15, 96.5, 7423.0, 7423.0), "FF": (105.48, 86.0, 6179.0, 6179.0)}.items():
    px, py = M["pitch_um"]
    nom = sp / 449.08 * (px + py) / 2
    der = (ocv_n / ocv_d) * (ins_qc / 28841.8) * Lp
    der_own = (ocv_n / ocv_d) * res[c]["max"]   # same OCV fraction on this tree's own modelled insertion
    print(c, "nominal %.2f derate(QC K_TREE) %.2f pair %.2f | derate on own insertion %.2f pair %.2f" % (nom, der, nom + der, der_own, nom + der_own))
