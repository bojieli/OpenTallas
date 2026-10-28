#!/usr/bin/env python3
"""QC-SMALLREG-1 12.14b ESTIMATE: balanced local H-tree (die_trial build_link_fishbone local='htree', ideal geometry,
no site legalisation) per region of MAP under the locality 'fish' feed.  Copy of DIE-KV-3 est_htree.py (main
results/die_kv_3_1027) with: V = 0.334 ps/um (DIE-QC-2 routed 1x M8, rep 250), clock x SC (12.15b x1.05), TT setup and FF
hold pessimism (clk_aocv g021 branch_pessimism on the branches below the pair LCA), droop shared inside a region (one
clock region = one droop region, 12.4a b1), KV calibration factor (H200B measured 98.6 / est 55.3) reported separately.
usage: est_sr.py PLAN MAP FEED OUT.json leaf_um..."""
import json, sys, math, collections
from pathlib import Path
import die_trial as D, schema as S, clk_aocv as CA
plan, regf, feedf, outf = sys.argv[1:5]
leafs = [float(x) for x in sys.argv[5:]] or [200.0]
P = S.Plan(S.load(plan), Path(plan))
reg = json.load(open(regf)); reg = reg.get("part_region", reg)
feed = json.load(open(feedf))
taps = D.clock_taps(P)
T = CA.load(str(Path(D.__file__).parent / "clk_aocv_table_g021.json"))
REP = 250.0; V = 0.334; T0 = 20.0; W_ = (V * REP - T0) / REP; SC = 1.05; KVCAL = 98.6 / 55.3
CS = {c: T["classes"]["A"][c]["cell_share"] for c in ("TT", "FF")}
FFK = 0.85      # FF clock delay / TT (est_b.py convention)


def run(leaf):
    n = D.build_link_fishbone(P, taps, reg, feed, local="htree", leaf_um=leaf)
    arr, stg = {}, {}
    reps = 0
    for i in sorted(n, key=lambda i: n[i]["level"]):
        d = n[i]
        if d["parent"] is None:
            arr[i], stg[i] = T0, 1
            continue
        p = n[d["parent"]]
        L = abs(p["x"] - d["x"]) + abs(p["y"] - d["y"])
        k = max(0, math.ceil(L / REP) - 1); reps += k
        arr[i] = arr[d["parent"]] + (k + 1) * T0 + W_ * L
        stg[i] = stg[d["parent"]] + k + 1
    tapinfo = {}
    for i, d in n.items():
        for t in d["taps"]:
            L = abs(t[2] - d["x"]) + abs(t[3] - d["y"])
            tapinfo[(t[0], t[1])] = dict(node=i, a=arr[i] + (0.5 * W_ * L * L / max(L, REP) if L else 0.0), leg=L)
    anc = {}
    for i in n:
        ch, j = [], i
        while j is not None:
            ch.append(j); j = n[j]["parent"]
        anc[i] = ch
    rroot = {d["region_root"]: i for i, d in n.items() if d.get("region_root")}
    per = {}
    for r in sorted(set(reg.values())):
        tl = [t for t in taps if reg[t[0]] == r]
        if len(tl) < 2:
            continue
        r0 = rroot[r]
        ins = [SC * (tapinfo[(t[0], t[1])]["a"] - arr[r0]) for t in tl]
        w = dict(hold=0.0, setup=0.0, nom=0.0)
        for a in tl:
            A = tapinfo[(a[0], a[1])]; sa = set(anc[A["node"]])
            for b in tl:
                if a is b:
                    continue
                B = tapinfo[(b[0], b[1])]
                lca = next(j for j in anc[B["node"]] if j in sa)
                dist = math.hypot(a[2] - b[2], a[3] - b[3])
                nom = SC * (B["a"] - A["a"])     # b later than a
                for c, mode in (("FF", "hold"), ("TT", "setup")):
                    k = SC * (1.0 if c == "TT" else FFK)
                    mk = lambda br, node: dict(cell_ps=k * br * CS[c], net_ps=k * br * (1 - CS[c]),
                                               stages={"A": max(1, stg[node] - stg[lca])})
                    pes = CA.branch_pessimism(T, c, mk(A["a"] - arr[lca], A["node"]), mk(B["a"] - arr[lca], B["node"]),
                                              dist, True, mode)
                    w[mode] = max(w[mode], (nom if c == "TT" else nom * FFK) + pes)
                w["nom"] = max(w["nom"], nom)
        bx = n[r0]["region"]
        per[r] = dict(taps=len(tl), box_um=[round(bx[2] - bx[0]), round(bx[3] - bx[1])], ins_max=round(max(ins)),
                      nom=round(w["nom"], 1), hold_FF=round(w["hold"], 1), setup_TT=round(w["setup"], 1),
                      spread=round(max(w["hold"], w["setup"]), 1))
    v = sorted(per.items(), key=lambda kv: -kv[1]["spread"])
    sp = [x["spread"] for _, x in v]
    return dict(leaf_um=leaf, nodes=len(n), repeaters=reps, regions=len(per), worst_spread=sp[0],
                p90=sp[len(sp) // 10], median=sp[len(sp) // 2], worst_cal=round(sp[0] * KVCAL, 1),
                over150_raw=sum(1 for s in sp if s > 150), over150_cal=sum(1 for s in sp if s * KVCAL > 150),
                ins_max=max(x["ins_max"] for _, x in v), worst5=v[:5], per_region=per)


res = [run(l) for l in leafs]
json.dump(res, open(outf, "w"), indent=1)
for r in res:
    print(json.dumps({k: x for k, x in r.items() if k not in ("per_region", "worst5")}))
    for k, x in r["worst5"][:4]:
        print("   ", k, json.dumps(x))
