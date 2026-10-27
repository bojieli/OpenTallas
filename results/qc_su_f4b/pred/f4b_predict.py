#!/usr/bin/env python3
"""QC-SU-F4B plan prediction (PLAN MODEL, UNCHECKED): frozen uf_phys (MODEL-REFIT-2 fit, vendored from
claude/qc-su-prog-l1-1026@d03d4aa38, unchanged) on the F4B layer plan, plus a STATED via-resistance estimate.
NOT a refit and no new model term: the via estimate is reported beside the model (MODEL-REFIT-3 owns the term).
  --layers m45 : tree legs on the M4/M5 average RC (the uf_phys default = what F4A was predicted with)
  --layers m56 : tree legs on the M5/M6 average RC (F4B plan: horizontal M6, vertical M5)
  seg_um = Manhattan length of every 2-pin leg (F4B legs are one L each; no maze detour on M6)
  via estimate (Elmore, full, no beta): per tree leg  Rstack*(C_net) + Rbend*(C_leg + cin) + Rstack*cin,
     Rstack = pin stack M1->leg layer (V1-V3 17.2 ohm, V4/V5 11.8 ohm: asap7 setRC.tcl), Rbend = one V5 (11.8 ohm),
     accumulated down the tree to every leaf; leaf nets unchanged (M2/M3).
usage: f4b_predict.py SPEC GEO LIBDIR OUT.json --layers m45|m56"""
import argparse, hashlib, json, statistics as st, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "model_ref"))
import uf_phys as U
import uf_phys_predict as UP
RC = dict(U.RC); RC["M6"] = (1.18796e-2, 1.87426e-1)        # asap7 setRC.tcl M6
VR = {"V1": 0.0172, "V2": 0.0172, "V3": 0.0172, "V4": 0.0118, "V5": 0.0118}   # kohm
ap = argparse.ArgumentParser(); ap.add_argument("spec"); ap.add_argument("geo"); ap.add_argument("libdir"); ap.add_argument("out")
ap.add_argument("--layers", choices=["m45", "m56"], required=True); a = ap.parse_args()
lay = ("M4", "M5") if a.layers == "m45" else ("M5", "M6")
U.R45 = 0.5 * (RC[lay[0]][0] + RC[lay[1]][0]) * U.KR
U.C45 = 0.5 * (RC[lay[0]][1] + RC[lay[1]][1]) * U.KC
LIBS = U.load_libs(a.libdir)
P0 = U.Plan(a.spec, a.geo, {})
seg = {n: U.man(v["xy"], P0.nodes[v["par"]]["xy"]) for n, v in P0.nodes.items() if v["par"]}
P = U.Plan(a.spec, a.geo, seg)

res = {}
for C in ("TT", "FF"):
    b = U.leaf_basis(P, LIBS, C, UP.PMAX, UP.PMIN)
    # via estimate per node (cumulative)
    rs = VR["V1"] + VR["V2"] + VR["V3"] + VR["V4"] + (VR["V5"] if lay[1] == "M6" else 0.0)
    dv = {"root": 0.0}; order = ["root"]; i = 0
    while i < len(order):
        order += P.kids.get(order[i], []); i += 1
    for n in order:
        v = P.nodes[n]
        if v["kind"] in ("leaf", "macro"):
            continue
        net = P.nets[n]; ch = P.kids[n]
        pincap = {net["pin"][c]: LIBS[C][P.nodes[c]["cell"]]["cin"] for c in ch}
        Cw, Cp, _, _ = U.rc_tree(net["pts"], net["edges"], pincap, U.R45, U.C45)
        for c in ch:
            cin = pincap[net["pin"][c]]
            if P.nodes[c]["kind"] in ("leaf", "macro"):
                dv[c] = dv[n] + rs * (Cw + Cp); continue
            dv[c] = dv[n] + rs * (Cw + Cp) + VR["V5"] * (U.C45 * seg.get(c, 0.0) + cin) + rs * cin
    for k in ("rise", "early", "late"):
        vals = b[k]; vv = {n: vals[n] + dv.get(n, 0.0) for n in vals}
        for tag, d in (("model", vals), ("model+via", vv)):
            x = list(d.values())
            res[f"{C}_{k}_{tag}"] = dict(mean=round(st.mean(x), 2), min=round(min(x), 2), max=round(max(x), 2), window=round(max(x) - min(x), 2))
    res[f"{C}_via_est_ps"] = dict(mean=round(st.mean(dv[n] for n in b["rise"]), 3), max=round(max(dv[n] for n in b["rise"]), 3))
band = dict(TT=(238.0, 262.0), FF=(187.5, 217.5))
g = res["TT_rise_model+via"]; f = res["FF_early_model+via"]
res["guard_band"] = dict(TT_rise=g["mean"], TT_window=g["window"], FF_early=f["mean"], FF_window=f["window"],
                         inside=band["TT"][0] <= g["mean"] <= band["TT"][1] and band["FF"][0] <= f["mean"] <= band["FF"][1] and g["window"] <= 20 and f["window"] <= 20)
res["layers"] = lay; res["R_leg_kohm_um"] = U.R45; res["C_leg_fF_um"] = U.C45
res["provenance"] = dict(argv=sys.argv, sha={p: hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16] for p in (a.spec, a.geo, __file__, U.__file__, UP.__file__)})
json.dump(res, open(a.out, "w"), indent=1)
print(a.layers, "TT rise %.2f w%.2f | FF early %.2f w%.2f | via est TT mean %.2f max %.2f ps | model-only TT %.2f w%.2f | guard band %s" % (
    g["mean"], g["window"], f["mean"], f["window"], res["TT_via_est_ps"]["mean"], res["TT_via_est_ps"]["max"],
    res["TT_rise_model"]["mean"], res["TT_rise_model"]["window"], "IN" if res["guard_band"]["inside"] else "OUT"))
