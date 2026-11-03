#!/usr/bin/env python3
"""DIE-HBM-61/MEM 11-03: plan-time macro-channel fit for the class-4 RE-FORM (right-width r0c0 masters).

Rule (COORD 06:38 / OWNER 11-03): a vertical channel between two macro faces is max(10.8, (pins_L + pins_R) x 0.048/2)
um (0.048 track pitch over the two vertical layers M3/M5, as DIE-HBM-61/PLAN mrow.py), a pinless face needs the
8.64 um halo only; macros on the core edge, std-cell area contiguous.  For each core: macros in an R x C grid
along one core edge (rows stacked N-S: W/E-pinned masters have no N/S pins -> 8.64 between rows), columns
separated by pin-count channels.  The grid is chosen to fit the CURRENT outline (no parent change) and leave the
largest contiguous std-cell band; fill = cell area / (outline - macro block).  No build.

    python3 channel_fit.py reform_v4.json OUT.json
"""
import json, math, sys
TP, FLOOR, HALO, EDGE = 0.024, 10.8, 8.64, 4.32
OLD = {"ot_sram_1r1w_64x512_m1_r2c2": (171.288, 77.784, 793), "ot_sram_1r1w_128x256_m1_r2c2": (94.824, 41.04, 410),
       "ot_sram_1r1w_256x256_m2_r2c2": (172.8, 41.04, 411)}
NEW = {"64x306": (106.056, 31.896, 314), "64x141": (56.184, 20.808, 149), "64x32": (23.112, 20.808, 40),
       "128x256": (91.8, 27.576, 265), "256x256": (169.368, 28.392, 266), "256x64": (53.16, 28.392, 74),
       "512x32": (53.16, 29.16, 43)}
# core -> list of (new master key, count) (instances measured on the d44o kit netlists)
USE = {"hfd_ep_static": [("64x306", 4)],
       "ot_hbm_host_cp_rxs": [("64x141", 4), ("256x256", 2)],   # yosys (OT_HBM_RW_MACROS): 4 llr leaves W 141 + 2 landing banks
       "ot_hfd_coll_q3_edge_core": [("64x141", 12)],
       "ot_hbm_su_programme_pslice_c5": [("128x256", 100)],
       "ot_hbm_su_static_sfustore_hw": [("512x32", 16)],
       "ot_hnx_idxn_keybuf_slice": [("256x256", 4), ("256x64", 1)],
       "ot_hbm_sm_vm_wr_q_t_lanes4": [("128x256", 1)],
       "ot_hbm_idx_rootctl_static_am": [("256x256", 1)]}


def ch(pl, pr):
    return HALO if pl + pr == 0 else max(FLOOR, (pl + pr) * TP)


def grid(ms, cols):
    """ms: list of (w,h,pins_per_edge) sorted; fill columns round-robin; width = sum col widths + channels."""
    C = [[] for _ in range(cols)]
    for i, m in enumerate(sorted(ms, key=lambda t: -t[0])):
        C[i % cols].append(m)
    C = [c for c in C if c]
    cw = [max(m[0] for m in c) for c in C]; pe = [max(m[2] for m in c) for c in C]
    chans = [ch(pe[0], 0)] + [ch(pe[i], pe[i + 1]) for i in range(len(C) - 1)] + [ch(pe[-1], 0)]
    W = sum(cw) + sum(chans) + 2 * EDGE
    H = max(sum(m[1] for m in c) + (len(c) - 1) * HALO for c in C) + HALO + EDGE
    return W, H, [round(x, 2) for x in chans], len(C), max(len(c) for c in C)


def up(v, s=8.64):
    return math.ceil(v / s - 1e-9) * s


def main(rin, out):
    R = {r["module"]: r for r in json.load(open(rin))}
    res = []
    for core, use in USE.items():
        r = R[core]; W0, H0 = r["old"]; gx, gy = r["room_xy"]; A = r["cell_area"]; pw, ph = r["pin_need_wh"]
        ms = [NEW[k] for k, n in use for _ in range(n)]
        mac = sum(m[0] * m[1] for m in ms)
        cands = []
        for cols in range(1, len(ms) + 1):
            bw, bh, chans, nc, nr = grid(ms, cols)
            for edge in ("S", "W"):     # macro block along the S (or, rotated grid, W) edge; std cells in one strip
                if edge == "S":
                    Wn = up(max(bw + 2 * EDGE, pw)); Hn = up(max(bh + A / 0.40 / Wn, ph, bh + 2 * EDGE))
                    blk = [bw, bh]
                else:
                    Hn = up(max(bw + 2 * EDGE, ph)); Wn = up(max(bh + A / 0.40 / Hn, pw, bh + 2 * EDGE))
                    blk = [bh, bw]
                asp = max(Wn, Hn) / min(Wn, Hn)
                fill = A / (Wn * Hn - mac)
                pin_bound = fill < 0.35 - 1e-6
                fp = Wn <= W0 + 2 * gx + 1e-6 and Hn <= H0 + 2 * gy + 1e-6
                cands.append(((not fp, asp > 3 + 1e-6, abs(fill - 0.40), Wn * Hn),
                              dict(cols=nc, rows=nr, block_edge=edge, block_um=[round(v, 2) for v in blk],
                                   channels_um=chans, max_channel_um=max(chans), outline_um=[round(Wn, 2), round(Hn, 2)],
                                   aspect=round(asp, 2), fill_of_free=round(fill, 3),
                                   bound="pins" if pin_bound else "fill",
                                   fits_parent=Wn <= W0 + 2 * gx + 1e-6 and Hn <= H0 + 2 * gy + 1e-6)))
        cands.sort(key=lambda t: t[0])
        best = cands[0][1]
        res.append(dict(core=core, outline_um=[W0, H0], cell_area_um2=A, pin_need_wh=[pw, ph], old_fill=r["old_fill"],
                        old_macro_area=r["macro_area"], new_macros=[f"{n}x {k}" for k, n in use], new_macro_area=round(mac),
                        max_pins_per_face_new=max(NEW[k][2] for k, _ in use),
                        fill_on_current_outline=round(A / (W0 * H0 - mac), 3), reshaped=best))
    json.dump(res, open(out, "w"), indent=1)
    for x in res:
        b = x["reshaped"]
        print(f"{x['core'][:30]:30s} mac {x['old_macro_area']}->{x['new_macro_area']} pins/face {x['max_pins_per_face_new']} "
              f"grid {b['cols']}c x{b['rows']}r @{b['block_edge']} maxch {b['max_channel_um']} -> {b['outline_um']} a{b['aspect']} "
              f"fill {x['old_fill']}->{b['fill_of_free']} {b['bound']} fitsparent {b['fits_parent']}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
