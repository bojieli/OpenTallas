#!/usr/bin/env python3
"""QC-SU-KITS-2: AS-BUILT prediction + kit spec for an adopted su_tree_uf plan (12.9 predict-before-build).

The su_tree_uf / su_kit_gate model gives every edge of a level the SAME wire T_l (short edges "detour"), but a detour
with no repeater on it is not enforceable: the router takes the shortest legal path between the two placed cells.
This tool keeps the plan unchanged (same k, islands, B / leaf sites, sizing, membership, repeater sites from G4) and
re-times it with what will actually be built:
  * island driver at the G2 legal island-rect centre (not the raw k-means point),
  * every segment between consecutive placed cells (node -> repeater -> ... -> child) = shortest legal maze path,
  * a driver with several branches loads the SUM of its branch wires (unequal branches), each branch end gets its own
    Elmore term,
  * leaf stage exactly as su_tree_uf (MST wire, pin caps, radius Elmore).
Same liberty NLDM + setRC 0.8/0.9 + MODEL-REFIT offsets TT +1.9 / FF -5.1 as su_kit_gate.  PLAN MODEL, UNCHECKED.
Validation mode (--equal) re-times with every segment = T_l / K_l and islands at the plan point; must reproduce the
su_tree_uf numbers exactly (proves the re-timing code is the same model).
Also emits the mscts_h spec (ot_ms_tree / ot_ms_leaves with frozen named membership / ot_ms_macros).
usage: uf_asbuilt.py GEO K LIBDIR UF_PY GATE.json OUT_PREFIX [--equal]
"""
import json
import math
import sys
from pathlib import Path

geo, K, libdir, uf_py, gate_js, outp = sys.argv[1:7]
EQUAL = "--equal" in sys.argv
K = int(K)
OFF = {"TT": 1.9, "FF": -5.1}
src = Path(uf_py).read_text()
assert "    return dict(k=k, islands=" in src
src = src.replace("    return dict(k=k, islands=", "    _CAPT[k] = (tree, groups, isl, Bc, leafc, Bs, nB, T1, T2, T3, K1, K2, K3)\n    return dict(k=k, islands=")
sys.argv = [uf_py, geo, "/dev/null", "100", str(K), str(K), "64", libdir]
g = {"__name__": "su_tree_uf_asbuilt", "__file__": uf_py, "_CAPT": {}}
sys.path.insert(0, str(Path(uf_py).parent))
exec(compile(src, uf_py, "exec"), g)
best = g["best"]
assert best["k"] in g["_CAPT"], "k changed by empty-group pruning"
tree, groups, isl, Bc, leafc, Bs, nB, T1, T2, T3, K1, K2, K3 = g["_CAPT"][best["k"]]
gate = json.loads(Path(gate_js).read_text())
LIBS, stage, interp, mst, man, md, cell, xy = (g[n] for n in ("LIBS", "stage", "interp", "mst", "man", "md", "cell", "xy"))
r, c, FFC, BIG, REP, SIZES = (g[n] for n in ("r", "c", "FFC", "BIG", "REP", "SIZES"))
entry, macros, sinks = g["entry"], g["macros"], g["sinks"]
k = best["k"]
sizing = best["sizing"]
ent = cell(entry)
edges = {e["edge"]: e for e in gate["gates"]["G4_detour_sites"]["edges"]}
isl_site = []
for q in range(k):
    if EQUAL:
        isl_site.append(isl[q])
    else:
        R = gate["gates"]["G2_island_rows"]["islands"][q]["rect_um"]
        isl_site.append(cell(((R[0] + R[2]) / 2, (R[1] + R[3]) / 2)))
T = {"L1": T1, "L2": T2, "L3": T3}
KK = {"L1": K1, "L2": K2, "L3": K3}

# ---- tree: node -> (parent, site cell, driver cell, level)
nodes = {"root": (None, ent, BIG, 0)}
order = ["root"]


def add_edge(lev, child, parent, csite, ccell):
    reps = edges[child]["repeaters"] if child in edges else []
    assert len(reps) == KK[lev] - 1, (child, len(reps), KK[lev])
    p = parent
    for j, rp in enumerate(reps):
        nm = f"{child}_r{j}"
        nodes[nm] = (p, cell(tuple(rp["xy"])), REP, lev)
        order.append(nm)
        p = nm
    nodes[child] = (p, csite, ccell, lev)
    order.append(child)


for q in range(k):
    add_edge("L1", f"Q{q}", "root", isl_site[q], sizing[f"Q_{q}"])
for (q, b) in Bs:
    add_edge("L2", f"Q{q}B{b}", f"Q{q}", Bc[(q, b)], sizing[f"B_{q}_{b}"])
leafg = {}
for q, b, l, lg in tree:
    nm = f"Q{q}B{b}L{l}"
    add_edge("L3", nm, f"Q{q}B{b}", leafc[(q, b, l)], BIG)
    leafg[nm] = lg
kids = {}
for n in order:
    if nodes[n][0]:
        kids.setdefault(nodes[n][0], []).append(n)


def seg(a, b):
    pa, pb = nodes[a], nodes[b]
    if EQUAL:
        return T[pb[3]] / KK[pb[3]]
    return md(pa[1], pb[1])


res = {}
for corner in ("TT", "FF"):
    L = LIBS[corner]
    arr = {"root": (0.0, 20.0)}           # arrival at node INPUT pin, input slew (model: ideal 20 ps at the root)
    leaf_t = {}
    for n in order:
        if n in leafg:
            continue
        t0, s0 = arr[n]
        ch = kids.get(n, [])
        dcell = nodes[n][2]
        ws = [seg(n, ch_) for ch_ in ch]
        if EQUAL:      # model: next pin = REP cin inside an edge, cin[BIG] at the edge end (whatever the child's size)
            cps = [L[REP]["cin"] if "_r" in ch_ else L[BIG]["cin"] for ch_ in ch]
        else:
            cps = [L[nodes[ch_][2]]["cin"] for ch_ in ch]
        if EQUAL:      # model form: fo branches of the SAME wire, each into its cp (all children share one cin)
            C = len(ch) * (c * ws[0] + cps[0]) if ch else 0.0
        else:
            C = sum(c * w + cp for w, cp in zip(ws, cps))
        Lc = L[dcell]
        d = 0.5 * (interp(Lc["rise"], s0, C) + interp(Lc["fall"], s0, C))
        so = interp(Lc["trise"], s0, C)
        for ch_, w, cp in zip(ch, ws, cps):
            arr[ch_] = (t0 + d + r * w * (c * w / 2 + cp), so)
    for nm, lg in leafg.items():
        t0, s3 = arr[nm]
        lc = xy(nodes[nm][1])
        wl = mst([lc] + [p[:2] for p in lg])
        C = c * wl + len(lg) * FFC[corner]
        LB = L[BIG]
        d = 0.5 * (interp(LB["rise"], s3, C) + interp(LB["fall"], s3, C))
        rad = sum(man(p, lc) for p in lg) / len(lg)
        leaf_t[nm] = round(t0 + d + r * rad * C / 2, 2)
    v = list(leaf_t.values())
    res[corner] = dict(mean_raw=round(sum(v) / len(v), 2), mean=round(sum(v) / len(v) + OFF[corner], 2), min=min(v),
                       max=max(v), window=round(max(v) - min(v), 2), leaf=leaf_t)

# ---- macro leaves: nearest leaf (maze) to the macro clock pin; designed leaf stage beside the pin, outside the row halo
mac = []
for line in open(geo):
    f = line.split()
    if f and f[0] == "MACRO":
        inst, x0, y0, x1, y1, px, py = f[1], *map(float, f[3:7]), float(f[8]), float(f[9])
        sx = x1 + 4.32 + 1.08 if abs(px - x1) < abs(px - x0) else x0 - 4.32 - 1.08
        site = (round(sx, 3), round(py, 3))
        best_leaf = min(leafg, key=lambda nm: md(nodes[nm][1], cell(site)))
        mac.append((inst, best_leaf, site))

out = dict(scope="AS-BUILT re-timing of the adopted su_tree_uf plan (shortest legal segment between placed cells, G2 "
                 "island centres, unequal-branch loads); liberty NLDM + setRC 0.8/0.9 + offsets TT+1.9/FF-5.1; PLAN "
                 "MODEL, UNCHECKED" if not EQUAL else "VALIDATION: equal-T re-timing (must equal su_tree_uf)",
           geo=geo, k=k, n_sinks=len(sinks), uf_pred=best["pred"], uf_pred_offset={
               cc: round(best["pred"][cc]["mean"] + OFF[cc], 2) for cc in ("TT", "FF")},
           asbuilt={cc: {a: b for a, b in v.items() if a != "leaf"} for cc, v in res.items()}, leaf=res,
           n_nodes=len(order) - 1 - len(leafg), n_leaves=len(leafg), macros=mac,
           seg_um={n: round(seg(nodes[n][0], n), 2) for n in order if nodes[n][0]})
Path(outp + ".json").write_text(json.dumps(out, indent=1))
print("uf", best["pred"]["TT"], best["pred"]["FF"])
print("ASBUILT" if not EQUAL else "EQUAL", {cc: out["asbuilt"][cc] for cc in ("TT", "FF")})

if not EQUAL:
    with open(outp + ".tcl", "w") as fo:
        fo.write("# QC-SU-KITS-2 mscts_h spec from the adopted su_tree_uf plan (k=%d) on the MIF0 placement %s;\n" % (k, geo))
        fo.write("# plan-computed cells (12.8 d1), frozen named membership, no measured input. Root = pushdown ot_ms_root.\n")
        fo.write("set ot_ms_port ck\nset ot_ms_root {%.3f %.3f}\nset ot_h_entry_n 0\n" % xy(ent))
        fo.write("set ot_h_fixed {\n {ot_ms_root %s %.3f %.3f}\n}\n" % ((BIG,) + xy(ent)))
        fo.write("set ot_ms_tree {\n")
        for n in order:
            if n == "root" or n in leafg:
                continue
            p, s, cl, _ = nodes[n]
            fo.write(" {%s %s %.3f %.3f %s}\n" % ((n, p) + xy(s) + (cl,)))
        fo.write("}\nset ot_ms_leaves {\n")
        for nm, lg in leafg.items():
            p, s, cl, _ = nodes[nm]
            regs = " ".join("{{%s} {%s}}" % (sk[2], sk[3]) for sk in lg)
            fo.write(" {%s %s {%.3f %.3f} {%s} %s}\n" % ((nm, p) + xy(s) + (regs, cl)))
        fo.write("}\nset ot_ms_macros {\n")
        for inst, lf, site in mac:
            fo.write(" {{%s} %s {%.3f %.3f}}\n" % (inst, lf, site[0], site[1]))
        fo.write("}\n")
    print("spec", outp + ".tcl", len(order) - 1 - len(leafg), "nodes", len(leafg), "leaves", len(mac), "macros")
