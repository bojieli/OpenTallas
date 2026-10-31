#!/usr/bin/env python3
"""DIE-HEAD-47: routed-region substitution into a die_sta_related proof (delta method).
For each cropped region R and corner C: delta(tap) = crop routed (DRT + OpenRCX) arrival - crop GRT arrival, both in the SAME
crop context (subtree below the region LCA, root port at LCA/A with the record slew).  The record tap arrival (die combo GRT)
gets this delta: late_ps += d_late, early_ps += d_early, fall_late_ps/fall_early_ps += d_fall_late.  Region-root CPPR node
ranges and taps outside the cropped regions are unchanged.  usage: subst.py PROOF_IN PROOF_OUT DRT_DIR [region...]"""
import json, shutil, sys
from pathlib import Path
src, dst, drt = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
regions = sys.argv[4:] or ["tW3b5", "tW1o1", "tW1o8"]
def rows(f):
    d = {}
    for l in open(f):
        x = l.split()
        if x and x[0] == "T":
            d[x[1]] = dict(late=float(x[2]), early=float(x[3]), fall=float(x[5]))
    return d
if dst.exists(): raise SystemExit(f"{dst} exists")
shutil.copytree(src, dst)
rep = {}
for C in ("TT", "FF"):
    pf = dst / f"tap_arrivals_{C}.json"; d = json.loads(pf.read_text())
    idx = {t["port"]: t for t in d["taps"]}
    for r in regions:
        g = rows(drt / (f"r6_{r}/out/arr_GRT_TT.txt" if C == "TT" else f"g_{r}/arr_GRT_FF.txt"))
        x = rows(drt / f"r6_{r}/out/arr_RCX_{C}.txt")
        taps = json.loads((drt / f"r6_{r}/reg.json").read_text())["taps"]
        dl = {t: x[t]["late"] - g[t]["late"] for t in taps}
        de = {t: x[t]["early"] - g[t]["early"] for t in taps}
        df = {t: x[t]["fall"] - g[t]["fall"] for t in taps}
        for t in taps:
            T = idx[t]; T["late_ps"] += dl[t]; T["early_ps"] += de[t]
            if "fall_late_ps" in T: T["fall_late_ps"] += df[t]; T["fall_early_ps"] += df[t]
            T["routed_delta_basis"] = "DIE-HEAD-47 crop DRT+OpenRCX minus crop GRT"
        rl = [idx[t]["late_ps"] for t in taps]
        rep.setdefault(r, {})[C] = dict(taps=len(taps), d_late_min=round(min(dl.values()), 2), d_late_max=round(max(dl.values()), 2),
                                        d_late_mean=round(sum(dl.values()) / len(dl), 2), d_rise_minus_fall_max=round(max(abs(dl[t] - df[t]) for t in taps), 2),
                                        routed_spread=round(max(rl) - min(rl), 2),
                                        grt_spread=round(max(rl[i] - dl[t] for i, t in enumerate(taps)) - min(rl[i] - dl[t] for i, t in enumerate(taps)), 2))
    d["routed_regions_basis"] = f"DIE-HEAD-47 delta method on {regions}"
    pf.write_text(json.dumps(d))
(dst / "routed_subst.json").write_text(json.dumps(rep, indent=1))
print(json.dumps(rep, indent=1))
