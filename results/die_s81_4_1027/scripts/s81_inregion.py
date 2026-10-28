#!/usr/bin/env python3
"""DIE-S81-3: IN-REGION clock spread estimate (COORD 21:38 CROSS-DIE NOTE, 12.14b estimate content, not a gate).

    s81_inregion.py --plan PLAN --map MAP --v-ps-mm 335 [--spice-scale TT=1.0485,FF=1.0552] --out OUT.json

Every intra-region port (src and dst partition in the same region) is a related pair under ONE region tree.  Entries =
partition centres.  Two region-tree forms, same shared OCV model as landed_phase_ocv (clk_aocv g021 table:
random A-class stages + 0.21 %/mm systematic on the bbox diagonal of the two entries + split node, nets flat; 12.3 core
latency 250 TT / 202.5 FF as class B on both sides; droop: one region = one droop -> same_region=True):
  htree : balanced equal-length H-tree from the region centre (locality.ins / htree_rem_um): nominal d = 0, unshared
          = the half-perimeter of the box where the two entries part.
  dme   : zero-skew tree over the region's REAL clock taps (die_trial.clock_taps of the plan, R4 grid + core taps), root
          at the region centre: insertion R = max Manhattan centre -> tap; conservatively every pair splits at the root
          (u = v R, d = 0) - the balanced local tree a CTS builds (no corner padding to the bbox).
  fish  : fishbone (long-axis trunk + perpendicular ribs, locality.fish_shared_um): nominal d = v (|pB - c| - |pA - c|).
spread (setup, TT) = max(|d + p_up|, |d - p_dn|); hold (FF) likewise with check='hold'.  Target <= ~150 ps.
"""
import argparse
import collections
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = [p for p in HERE.parents if (p / "tools" / "die_plan" / "locality.py").exists()][0]
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
import locality as LO  # noqa: E402

CA = LO.CA


def branch(T, corner, u, core_lat):
    B = T["classes"]["B"][corner]
    fc = T["classes"]["A"][corner]["cell_share"]
    mu = T["classes"]["A"][corner]["mu_stage_ps"]
    nA = max(1, int(round(u / mu))) if u > 0 else 0
    nB = max(1, round(core_lat / B["mu_stage_ps"]))
    st = {"B": nB}
    if nA:
        st["A"] = nA
    return dict(cell_ps=fc * u + B["cell_share"] * core_lat, net_ps=(1 - fc) * u + (1 - B["cell_share"]) * core_lat,
                stages=st, unshared_ps=u)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--map", required=True)
    ap.add_argument("--map-key", default=None)
    ap.add_argument("--v-ps-mm", type=float, default=335.0)
    ap.add_argument("--spice-scale", default="TT=1.0,FF=1.0")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    D = LO.load_plan(a.plan)
    m = json.loads(Path(a.map).read_text())
    if a.map_key:
        m = m[a.map_key]
    reg = LO.load_regions(m, D)
    G = LO.region_geom(D, reg)
    Tt = CA.load(LO.TABLE)
    sc = {k: float(v) for k, v in (kv.split("=") for kv in a.spice_scale.split(","))}
    ffs = Tt["classes"]["A"]["FF"]["mu_stage_ps"] / Tt["classes"]["A"]["TT"]["mu_stage_ps"]
    v = a.v_ps_mm
    import die_trial as DT
    import schema as S
    PP = S.Plan(S.load(a.plan), Path(a.plan))
    Rt = collections.defaultdict(float)
    for part, port, x, y in DT.clock_taps(PP):
        rr = reg[part]
        Rt[rr] = max(Rt[rr], LO.manh((x, y), G[rr]["cen"]))
    seen = set()
    rows = []
    for q in D["ports"]:
        r = reg[q["src"]]
        if r != reg[q["dst"]]:
            continue
        key = (q["src"], q["dst"])
        if key in seen:
            continue
        seen.add(key)
        g = G[r]
        pA, pB = D["parts"][q["src"]]["cen"], D["parts"][q["dst"]]["cen"]
        c = g["cen"]
        row = dict(region=r, src=q["src"], dst=q["dst"], w_mm=round(g["w"] / 1000, 2), h_mm=round(g["h"] / 1000, 2))
        for form in ("htree", "dme", "fish"):
            if form == "dme":
                ua = ub = v * Rt[r] / 1000.0
                split_xy = c
            elif form == "htree":
                rem = min(LO.htree_rem_um(g["bbox"], pA, pB), (g["w"] + g["h"]) / 2)
                ua = ub = v * rem / 1000.0
                split_xy = c
            else:
                sh = LO.fish_shared_um(g, pA, pB)
                ua = v * (LO.manh(pA, c) - sh) / 1000.0
                ub = v * (LO.manh(pB, c) - sh) / 1000.0
                split_xy = c
            pts = [pA, pB, split_xy]
            dist = math.hypot(max(p[0] for p in pts) - min(p[0] for p in pts), max(p[1] for p in pts) - min(p[1] for p in pts))
            for corner, chk in (("TT", "setup"), ("FF", "hold")):
                s = sc[corner] * (1.0 if corner == "TT" else ffs)
                bra, brb = branch(Tt, corner, ua * s, LO.CORE_LAT[corner]), branch(Tt, corner, ub * s, LO.CORE_LAT[corner])
                d = (ub - ua) * s
                pu = CA.branch_pessimism(Tt, corner, brb, bra, dist, True, chk)
                pdn = CA.branch_pessimism(Tt, corner, bra, brb, dist, True, chk)
                row[f"{form}_{corner}_d"] = round(d, 1)
                row[f"{form}_{corner}_spread"] = round(max(abs(d + pu), abs(d - pdn)), 1)
                row[f"{form}_{corner}_u"] = round(max(ua, ub) * s, 1)
        rows.append(row)
    summ = dict(plan=a.plan, map=a.map, v_ps_mm=v, spice=sc, pairs=len(rows), regions=len(G))
    per_reg = collections.defaultdict(dict)
    for form in ("htree", "dme", "fish"):
        for corner in ("TT", "FF"):
            k = f"{form}_{corner}_spread"
            vals = [r[k] for r in rows]
            summ[f"{k}_max"] = max(vals)
            summ[f"{k}_p95"] = sorted(vals)[int(0.95 * (len(vals) - 1))]
            summ[f"{k}_over150"] = sum(1 for x in vals if x > 150)
            for r in rows:
                per_reg[r["region"]][k] = max(per_reg[r["region"]].get(k, 0), r[k])
    worst = sorted(per_reg.items(), key=lambda kv: -max(kv[1]["htree_TT_spread"], kv[1]["htree_FF_spread"]))[:12]
    summ["worst_regions_htree"] = [dict(region=k, w_mm=round(G[k]["w"] / 1000, 2), h_mm=round(G[k]["h"] / 1000, 2),
                                        R_tap_um=round(Rt[k], 1), **v_) for k, v_ in worst]
    summ["regions_dme_over150"] = sorted(k for k, v_ in per_reg.items()
                                         if max(v_["dme_TT_spread"], v_["dme_FF_spread"]) > 150)
    summ["dme_R_um_phy"] = {k: round(x, 1) for k, x in Rt.items() if G[k]["hard"] or G[k]["w"] > 8000}
    summ["regions_htree_over150"] = sorted(k for k, v_ in per_reg.items()
                                           if max(v_["htree_TT_spread"], v_["htree_FF_spread"]) > 150)
    Path(a.out).write_text(json.dumps(dict(summary=summ, rows=rows), indent=0))
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
