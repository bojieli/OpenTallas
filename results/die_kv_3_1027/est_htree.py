#!/usr/bin/env python3
"""DIE-KV-3 12.14b ESTIMATE (analytic, before any GRT/STA): balanced local H-tree inside each land128 region under the
link feed vs the DIE-KV-2 fishbone.  Geometry = the die_trial builder itself (no placement/site slide); delay = stage
model calibrated to the LAND-KV-1 measured trunk (321 ps/mm at rep 250 um: t0 + w*L per stage); OCV = main clk_aocv
branch_pessimism with the APPROVED g021 table on the branches below each pair's LCA (cell share from the table, class A),
droop 0 (droop region = clock region, shared rule).  Pairs = every ordered tap pair inside one PARTITION (die STA 'intra')
and inside one REGION (incl. seam pairs of 2-partition regions).
est_htree.py PLAN REGIONS FEED OUT.json [leaf_um ...]"""
import json, sys, math, collections
from pathlib import Path
import die_trial as D, schema as S, clk_aocv as CA

plan, regf, feedf, outf = sys.argv[1:5]
leafs = [float(x) for x in sys.argv[5:]] or [150.0, 200.0, 300.0]
P = S.Plan(S.load(plan), Path(plan))
reg = json.load(open(regf))["part_region"]
feed = json.load(open(feedf))
taps = D.clock_taps(P)
T = CA.load(str(Path(D.__file__).parent / "clk_aocv_table_g021.json")) if hasattr(CA, "load") else \
    json.load(open(Path(D.__file__).parent / "clk_aocv_table_g021.json"))["clock_aocv"]
REP = 250.0
V = 0.321                       # ps/um, measured trunk incl. repeaters (LAND-KV-1)
T0 = 20.0                       # ps per stage intrinsic (BUFx24 into a short leg), rest wire
W_ = (V * REP - T0) / REP       # ps/um so that a 250-um stage = 80.25 ps
CELL_SHARE = T["classes"]["A"]["TT"]["cell_share"]


def run(local, leaf):
    n = D.build_link_fishbone(P, taps, reg, feed, local=local, leaf_um=leaf) if local == "htree" else \
        D.build_link_fishbone(P, taps, reg, feed)
    # per node: arrival from the tree root, stages
    arr, stg, wire = {0: T0}, {0: 1}, {0: 0.0}
    order = sorted(n, key=lambda i: n[i]["level"])
    reps = 0
    for i in order:
        d = n[i]
        if d["parent"] is None:
            continue
        p = n[d["parent"]]
        L = abs(p["x"] - d["x"]) + abs(p["y"] - d["y"])
        k = max(0, math.ceil(L / REP) - 1)
        reps += k
        arr[i] = arr[d["parent"]] + (k + 1) * T0 + W_ * L
        stg[i] = stg[d["parent"]] + k + 1
        wire[i] = wire[d["parent"]] + L
    rroot = {d["region_root"]: i for i, d in n.items() if d.get("region_root")}
    tapinfo = {}
    for i, d in n.items():
        for t in d["taps"]:
            L = abs(t[2] - d["x"]) + abs(t[3] - d["y"])
            tapinfo[(t[0], t[1])] = dict(node=i, a=arr[i] + 0.5 * W_ * L * L / max(L, REP) if L else arr[i], leg=L)
    # ancestors
    anc = {}
    for i in n:
        ch, j = [], i
        while j is not None:
            ch.append(j)
            j = n[j]["parent"]
        anc[i] = ch
    nodes_in = collections.Counter()
    for i, d in n.items():
        if d.get("rib") is not None:
            nodes_in[d["rib"]] += 1
    per_reg = {}
    worst = dict(intra=0.0, region=0.0)
    for r in sorted(set(reg.values())):
        tl = [t for t in taps if reg[t[0]] == r]
        if not tl:
            continue
        r0 = rroot[r]
        ins = [tapinfo[(t[0], t[1])]["a"] - arr[r0] for t in tl]
        sp = dict(intra=0.0, region=0.0, intra_nom=0.0, region_nom=0.0)
        for a in tl:
            for b in tl:
                if a is b:
                    continue
                A, B = tapinfo[(a[0], a[1])], tapinfo[(b[0], b[1])]
                sa = set(anc[A["node"]])
                lca = next(j for j in anc[B["node"]] if j in sa)
                ba = A["a"] - arr[lca]
                bb = B["a"] - arr[lca]
                mk = lambda br, node: dict(cell_ps=br * CELL_SHARE, net_ps=br * (1 - CELL_SHARE),
                                           stages={"A": max(1, stg[node] - stg[lca])})
                dist = math.hypot(a[2] - b[2], a[3] - b[3])
                pes = CA.branch_pessimism(T, "FF", mk(ba, A["node"]), mk(bb, B["node"]), dist, True, "hold")
                nom = A["a"] - B["a"]       # capture b late vs launch a early: hold skew = arr_b - arr_a
                tot = -nom + pes
                cls = "intra" if a[0] == b[0] else "region"
                sp[cls] = max(sp[cls], tot)
                sp[cls + "_nom"] = max(sp[cls + "_nom"], abs(nom))
        per_reg[r] = dict(taps=len(tl), parts=len({t[0] for t in tl}), ins_min=round(min(ins), 1), ins_max=round(max(ins), 1),
                          spread_hold_ps=round(max(sp["intra"], sp["region"]), 1), intra_ps=round(sp["intra"], 1),
                          nom_ps=round(max(sp["intra_nom"], sp["region_nom"]), 1),
                          box_um=[round(v) for v in n[r0]["region"]])
        worst["intra"] = max(worst["intra"], sp["intra"])
        worst["region"] = max(worst["region"], sp["region"])
    feed_wire = n[0]["link_feed"]["feed_wire_um"]
    tot_wire = sum(abs(d["x"] - n[d["parent"]]["x"]) + abs(d["y"] - n[d["parent"]]["y"]) for d in n.values() if d["parent"] is not None)
    v = sorted(per_reg.values(), key=lambda x: -x["spread_hold_ps"])
    return dict(local=local, leaf_um=leaf, nodes=len(n), repeaters=reps, buffers=len(n) + reps,
                wire_mm=round(tot_wire / 1000, 1), feed_wire_mm=round(feed_wire / 1000, 1),
                region_wire_mm=round((tot_wire - feed_wire) / 1000, 1),
                last_mile_mm=round(sum(x["leg"] for x in tapinfo.values()) / 1000, 1),
                worst_intra_hold_spread_ps=round(worst["intra"], 1), worst_region_hold_spread_ps=round(worst["region"], 1),
                regions_over_150=sum(1 for x in v if x["spread_hold_ps"] > 150), ins_max_ps=max(x["ins_max"] for x in v),
                ins_p50_ps=sorted(x["ins_max"] for x in v)[len(v) // 2], worst5=[dict(region=k, **x) for k, x in
                sorted(per_reg.items(), key=lambda kv: -kv[1]["spread_hold_ps"])[:5]], per_region=per_reg)


res = [run("fishbone", 0)] + [run("htree", l) for l in leafs]
json.dump(res, open(outf, "w"), indent=1)
for r in res:
    print(json.dumps({k: v for k, v in r.items() if k not in ("per_region", "worst5")}))
    print("   worst:", json.dumps(r["worst5"][:3]))
