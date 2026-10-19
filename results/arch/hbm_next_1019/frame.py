#!/usr/bin/env python3
"""HBM-NEXT study (10-19), check (e): die area and floorplan aspect at P lanes (arithmetic, no tools).

Base: d4g plan (main results/arch/hbm_die_d4g/plan/plan_geometry.json d4g_phy): die 20,200 x 31,773.52 um; two SM
bands (S, N) of 8 SM columns 1,939.68 x 6,955.2 um; 961 um empty side margins in each SM band; inter-column gaps
2,760.56 um a band; hub band between them (placed density ~0.56).  Reticle 26 x 33 mm, 500 um margin required
(eval.json reticle.margin_req_um) -> W <= 25,500, H <= 32,500.
Per added lane the SM column grows by 345.6 x 6,955.2 um (D2 rp4lp2: +86.4 um a tile x 4 tiles across, measured cells).

Frames:
  F-A  x-only growth (D2 recommendation at P = 2): W = 20,200 + 8 x 345.6 (P-1) - 1,922 (margins absorbed first).
  F-C  clean slate: SM column width cw chosen, height = column area / cw; die width = 8 cw + 2,760.56;
       hub band re-packed to the wider die at the SAME density (hub band 13.35 mm x 20.2 mm -> 13.35 x 20.2 / W).
       H = 31,773.52 + 2 (ch - 6,955.2) - (13,350 - 13,350 x 20,200 / W).
"""
import json, sys

COLW, COLH, LANE_DW = 1939.68, 6955.2, 345.6
W0, H0, MARG, GAPS, HUB_H = 20200.0, 31773.52, 1922.0, 2760.56, 13350.0
WMAX, HMAX = 25500.0, 32500.0
D1_DIE = {1: 641.8, 2: 676.4, 4: 742.9, 6: 809.5, 8: 876.3}


def frames(P):
    area = COLW * COLH + (P - 1) * LANE_DW * COLH
    fa_w = W0 + max(0.0, 8 * LANE_DW * (P - 1) - MARG)
    out = dict(P=P, d1_die_mm2=D1_DIE[P], col_area_mm2=round(area / 1e6, 3),
               FA=dict(W=round(fa_w), H=round(H0), mm2=round(fa_w * H0 / 1e6, 1), fits=fa_w <= WMAX))
    best = None
    for cw in [x * 43.2 for x in range(45, 70)]:            # column width on the 43.2 um lattice
        W = 8 * cw + GAPS
        if W > WMAX:
            break
        ch = area / cw
        H = H0 + 2 * (ch - COLH) - (HUB_H - HUB_H * W0 / W)
        tile = ((cw - 108.0) / 4, (ch - 561.6) / 4)
        c = dict(cw=round(cw, 2), ch=round(ch), W=round(W), H=round(H), mm2=round(W * H / 1e6, 1),
                 col_aspect=round(ch / cw, 2), tile_um=[round(tile[0], 1), round(tile[1], 1)],
                 tile_aspect=round(tile[1] / tile[0], 2), margins_um=[round(26000 - W), round(33000 - H)])
        if H <= HMAX and (best is None or c["mm2"] < best["mm2"]):
            best = c
    out["FC_best"] = best
    out["reticle_usable_fraction_of_d1_die"] = round(D1_DIE[P] / (WMAX * HMAX / 1e6), 3)
    return out


if __name__ == "__main__":
    res = [frames(P) for P in (1, 2, 4, 6, 8)]
    print(json.dumps(res, indent=1))
    if len(sys.argv) > 1:
        open(sys.argv[1], "w").write(json.dumps(dict(schema="opentallas.hbm_next_1019.frame.v1", rule=__doc__, rows=res), indent=1) + "\n")
