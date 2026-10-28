#!/usr/bin/env python3
"""DIE-S81-8 NUMBER-CHECK (packed-G): does the count-aligned (CA) gate margin include clock OCV (0.21 %/mm AOCV table)
+ droop on the unshared clock?  And what makes the declared-budget FF intra hold -162.5?

Uses main tools/die_plan/die_sta_related.py unchanged (imported).  Steps per corner (spice-scaled taps, --cppr-lca):
 (A) gate form: count_align_landed(... key=region) exactly as die_sta_related --count-align (no explicit AOCV term).
 (B) same, but every landed tap pair's d interval is widened by the main clock_ocv_fn(table, shared droop, mesh regions)
     pessimism: d_lo -= ocv(a,b,'setup'), d_hi += ocv(a,b,'hold')  (upper bound: may double count the OpenSTA min/max
     spread already in late/early).
 (C) intra FF hold decomposition per partition: zero-logic declared slack = ea+cq_min-(lc+hold)-unc+cr-ocv; per
     partition worst, base (zero skew) term, damage and ocv shares.
usage: nc_ca_ocv.py TOOLS PROOF PLAN BIND OUT.json
"""
import json, sys, math
from pathlib import Path
from collections import defaultdict

tools, proof, plan_p, bind_p, out_p = sys.argv[1:6]
sys.path.insert(0, tools)
import die_sta_related as D  # noqa: E402

D.CPPR_LCA = True
plan = json.loads(Path(plan_p).read_text())
bind = json.loads(Path(bind_p).read_text())
period = 833.333
res = {}
for c in ("TT", "FF"):
    meta, taps = D.load_taps(Path(proof), c)
    meta, taps = D.scale_clock(meta, taps, D.SPICE_CLOCK_CAL[c])
    rng = meta["cppr_node_range_ps"]
    pairs, _ = D.build_pairs(plan, taps)
    dreg = D.droop_regions(Path(proof), taps, "mesh", str(Path(proof) / "droop_regions.json"))
    lat = 250.0 if c == "TT" else 202.5
    ocv = D.clock_ocv_fn("table", "shared", dict(meta, corner=c), taps, lat, region=dreg)
    reg = json.loads((Path(out_p).parent / f"reg_{c}.json").read_text())
    A = D.count_align_landed(pairs["landed"], taps, bind, period, reg, cppr_range=rng, key="region")
    orig = D.count_align_d_intervals
    pocv = defaultdict(lambda: [0.0, 0.0])

    def widened(landed, taps_, cppr_range=None, part_region=None):
        out = {}
        for a, b, tag in landed:
            TA, TB = taps_[a], taps_[b]
            if part_region is not None:
                tag = f"{part_region[TA['part']]}->{part_region[TB['part']]}"
            node = D.pair_node(TA, TB)
            la, ea, lc, ec = D.arr4(TA, TB, node)
            cr = D.credit(cppr_range, node, la, ea, lc, ec) if cppr_range else 0.0
            os_, oh = ocv(a, b, "setup"), ocv(a, b, "hold")
            p = pocv[tag]
            p[0], p[1] = max(p[0], os_), max(p[1], oh)
            lo, hi = ec - la + cr - os_, lc - ea - cr + oh
            o = out.get(tag)
            out[tag] = (lo, hi) if o is None else (min(o[0], lo), max(o[1], hi))
        return out
    D.count_align_d_intervals = widened
    B = D.count_align_landed(pairs["landed"], taps, bind, period, reg, cppr_range=rng, key="region")
    D.count_align_d_intervals = orig
    rowsA = {r["port"]: r for r in A["rows"]}
    worstB = sorted(B["rows"], key=lambda r: min(r["margin_lo_ps"], r["margin_hi_ps"]))[:15]
    for r in worstB:
        r["gate_margin_lo_ps"] = rowsA[r["port"]]["margin_lo_ps"]
        r["ocv_setup_ps"], r["ocv_hold_ps"] = [round(x, 1) for x in pocv[r["tag"]]]
    nB = sum(1 for r in B["rows"] if min(r["margin_lo_ps"], r["margin_hi_ps"]) < 100)
    # (C) intra hold per partition
    part = defaultdict(lambda: dict(n=0, neg=0, worst=1e9, w=None))
    base = reg["clkq_min_nowire_ps"] - reg["hold_ps"] - D.UNC_HOLD_PS
    for a, b, tag in pairs["intra"]:
        TA, TB = taps[a], taps[b]
        node = D.pair_node(TA, TB)
        la, ea, lc, ec = D.arr4(TA, TB, node)
        cr = D.credit(rng, node, la, ea, lc, ec)
        dmg = lc - ea - cr
        oh = ocv(a, b, "hold")
        h = base - dmg - oh
        P = part[TA["part"]]
        P["n"] += 1
        P["neg"] += h < 0
        if h < P["worst"]:
            P["worst"], P["w"] = h, dict(launch=a, capture=b, damage_ps=round(dmg, 1), ocv_ps=round(oh, 1))
    pl = sorted(((v["worst"], k, v) for k, v in part.items()))
    hist = defaultdict(int)
    for w, k, v in pl:
        hist["<-150" if w < -150 else "-150..-100" if w < -100 else "-100..-50" if w < -50 else "-50..0" if w < 0 else ">=0"] += 1
    res[c] = dict(
        gate_A=dict(verdict=A["verdict"], fail=A["fail"], unbound=A["unbound"], no_taps=A["no_taps"],
                    start_skew_fail=A["start_skew"]["fail"], worst_lo=A["worst_lo"], worst_hi=A["worst_hi"]),
        with_ocv_B=dict(verdict=B["verdict"], fail=B["fail"], below100=nB, worst=worstB,
                        ocv_max_setup_ps=round(max(p[0] for p in pocv.values()), 1),
                        ocv_max_hold_ps=round(max(p[1] for p in pocv.values()), 1)),
        hold_intra=dict(base_zero_skew_ps=round(base, 2), partitions=len(pl), worst_partition_hist=dict(hist),
                        worst20=[dict(part=k, worst_ps=round(w, 1), pairs=v["n"], neg=v["neg"], **v["w"]) for w, k, v in pl[:20]]))
    print(c, "A", A["verdict"], A["fail"], A["worst_lo"]["margin_lo_ps"], "B", B["verdict"], B["fail"], nB,
          worstB[0]["port"], worstB[0]["margin_lo_ps"], worstB[0]["margin_hi_ps"], "hold base", round(base, 2), dict(hist))
Path(out_p).write_text(json.dumps(res, indent=1))
