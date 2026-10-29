#!/usr/bin/env python3
"""DIE-QC-6 INFO diagnostic (main die_sta_related functions, unchanged): intra pair hold/setup with ONE physical endpoint
model per tap: a core tap ('__clk_c*') mapped to a signed SU core -> that core's ETM only; every other tap -> the
declared budget register (main's register numbers, read from a finished main run).  --early TSV: shift each viewed core
tap by -early_<corner> (CORELAT-SQ-1 signed-mean early tap) before timing (what-if of the bound plan).
usage: rv_phys.py TOOLS PROOF PLAN VIEWS_DIR PAIRS_PKL MAIN_RUN_JSON [--early qc_core_taps.tsv]"""
import sys, json, pickle, collections, csv
from pathlib import Path

sys.path.insert(0, sys.argv[1])
import die_sta_related as R
import schema as S_

R.CPPR_LCA = True
P, plan_p, VD, pk, mainj = Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4]), sys.argv[5], sys.argv[6]
early = {}
if "--early" in sys.argv:
    for r in csv.DictReader(open(sys.argv[sys.argv.index("--early") + 1]), delimiter="\t"):
        if r["early_TT"] not in ("None", ""):
            early[r["module"]] = {"TT": float(r["early_TT"]), "FF": float(r["early_FF"])}
plan = json.loads(Path(plan_p).read_text())
M = json.loads(Path(mainj).read_text())
mods = sorted(d.name for d in VD.iterdir() if d.is_dir())
pairs = sorted({k[:3] for k in pickle.load(open(pk, "rb"))["calls"][0]["ff"]})


def cls(p):
    return "c_*" if p.startswith("c_") else ("sl_*_su_c" if p.endswith("su_c") else ("sl_*" if p.startswith("sl_") else "other"))


BINS = (-1e9, -150, -100, -75, -50, -25, 0, 1e9)
for c in ("TT", "FF"):
    meta, taps = R.load_taps(P, c)
    meta, taps = R.scale_clock(meta, taps, R.SPICE_CLOCK_CAL[c])
    rng = meta["cppr_node_range_ps"]
    reg = M["corners"][c]["register"]
    lat = S_.common_latency_ps(S_.Plan(plan), c)
    budget = R.budget_model(reg, lat)
    cmap = R.map_cores_to_taps(plan, taps)
    tapmod = {}
    for (n, inst), (m, port, dist, pf) in cmap.items():
        if m in mods and port and "__clk_c" in port:
            tapmod.setdefault(port, set()).add(m)
    shifted = 0
    if early:
        for port, ms in tapmod.items():
            e = max(early.get(m, {}).get(c, 0.0) for m in ms)
            if e:
                shifted += 1
                for k in R.TAP_TIME_KEYS:
                    if k in taps[port]:
                        taps[port][k] = float(taps[port][k]) - e
    models = {m: R.core_view_model(m, VD / m, c, 1.2, 0.0) for m in mods}
    dreg = R.droop_regions(P, taps, "mesh", str(P / "droop_regions.json"))
    ocv = R.clock_ocv_fn("table", "shared", dict(meta, corner=c), taps, lat, region=dreg)

    def mlist(p):
        return [models[m] for m in sorted(tapmod[p])] if p in tapmod else [budget]
    agg = collections.defaultdict(list)
    for a, b, tag in pairs:
        A, B_ = taps[a], taps[b]
        node = R.pair_node(A, B_)
        la, ea, lc, ec = R.arr4(A, B_, node)
        cr = R.credit(rng, node, la, ea, lc, ec)
        combos = R.endpoint_slacks(A, B_, la, ea, lc, ec, cr, R.PERIOD_PS if hasattr(R, "PERIOD_PS") else M["period_ps"],
                                   M["unc_setup_ps"], M["unc_hold_ps"], mlist(a), mlist(b))
        s = min(x[0] for x in combos) - ocv(a, b, "setup")
        h = min(x[1] for x in combos) - ocv(a, b, "hold")
        kind = "core-core" if (a in tapmod and b in tapmod) else ("core-glue" if (a in tapmod or b in tapmod) else "glue-glue")
        agg[(cls(tag), kind)].append((h, s, a, b, tag))
    print(f"## {c} lat {lat} viewed core taps {len(tapmod)} shifted {shifted} early={bool(early)}")
    for k in sorted(agg):
        L = sorted(agg[k])
        hist = [sum(1 for x in L if lo <= x[0] < hi) for lo, hi in zip(BINS, BINS[1:])]
        print(f"  {k[0]:10s} {k[1]:9s} n {len(L):6d} worst hold {L[0][0]:7.1f} ({L[0][2]}->{L[0][3]}) neg {sum(1 for x in L if x[0] < 0):6d} "
              f"median {L[len(L)//2][0]:6.1f} | worst setup {min(x[1] for x in L):7.1f} | hold hist <-150,-100,-75,-50,-25,0,>=0: {hist}")
