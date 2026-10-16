#!/usr/bin/env python3
"""H-SM-REPACK 2026-10-15: SM tile / frame re-pack geometry (one source for the kit generator, the analysis and the
renders).  All child outlines are the CLOSED LEF SIZEs on main (read from the views); no new master is introduced.

Tile rp1 = ot_hbm_accel_smh_tile_eg (DEDUPE: wg is the same RTL, placed MY in the frame), 18 -> 12 hard children:
  2 leaves x {xs, bdc, tct, tcl, tcl} (closed views of the r16/cpt kits) stacked N-S, leaf 1 MX,
  2 x ot_smh_tr_group_beat_e (closed 43.2 x 216, native PASS) = the W transit and the E beat stage, side by side at the
  E end of the transport channel; rows / landings / pin registers are tile cells (parent sinks ~14.6k <= 15k).
Coordinates in um, origin lower-left, eg orientation (rin/bin W face, rout/bout E face)."""
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V = "physical/ref_tile/{}/views/{}"
VIEWS = {"xs": V.format("smh_xs_ref_p45m", "ot_hbm_accel_smh_xs"),
         "bdc": V.format("smh_bdc_ref_p50", "ot_hbm_accel_smh_bdc"),
         "tcl": V.format("smh_tcl_ref_p45", "ot_hbm_accel_smh_tcl"),
         "tct": V.format("smh_tct_ref_p45", "ot_hbm_accel_smh_tct"),
         "beat": V.format("smh_tr_group_beat_e_ref", "ot_smh_tr_group_beat_e")}


def lef_size(view):
    t = (ROOT / view / f"{Path(view).name}.lef").read_text()
    m = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", t)
    return float(m.group(1)), float(m.group(2))


DIM = {k: lef_size(v) for k, v in VIEWS.items()}
G = 8.64                       # child origin lattice (spec child_lattice_um): lcm of site, row and M1-M7 tracks
W = 397.44                     # 46 x 8.64 (E station column beside the tcl); every child >= 20 um from the core edge (all four faces carry pins)
X0 = 25.92                     # leaf column origin
YB = 25.92                     # S margin (leaf-1 tcl inputs face S after MX)
# leaf 0 (R0, relative to the xs0 origin): xs bottom; bdc above xs (58.32-um operand-relay gap, cpt leaf 0); tct beside
# bdc; the two tcl above tct (tcl sum_o S face -> tct sum_i N face); tcl i_w/i_x on their N face (edge channel)
LEAF0 = [("xs", "u_xs", 0.0, 0.0), ("bdc", "u_bdc", 0.0, 216.0), ("tct", "u_tcc.u_tr", 112.32 + 25.92, 216.0),
         ("tcl", "u_tcc.u_h0", 138.24, 311.04), ("tcl", "u_tcc.u_h1", 250.56, 311.04)]
# leaf 1, absolute y on the lattice, bottom-up: tct (R0; MX puts 18 of its pins off track) | tcl x2 (R0: sum_o S ->
# tct N, i_w/i_x N face toward the x store) | bdc beside (MX: operands up) | xs (MX: bk1 / rl1 face the channel)
LEAF1 = [("tct", "u_tcc.u_tr", 138.24, YB, "R0"), ("tcl", "u_tcc.u_h0", 138.24, 120.96, "R0"),
         ("tcl", "u_tcc.u_h1", 250.56, 120.96, "R0"), ("bdc", "u_bdc", 0.0, 103.68, "MX"), ("xs", "u_xs", 0.0, 311.04, "MX")]
Y_CH0 = round(311.04 + 157.68, 3)          # channel bottom = xs1 top (468.72)
# VARIANT rp1: rows + N/S landings are tile cells (parent sinks ~14.6k).  rp2 (A/B, clock-safe): the two landings are the
# CLOSED ot_smh_tr_group_land master too (216 x 43.2, q face on the x store's bk1 face), stacked in the channel ->
# parent sinks ~10.4k, channel +138.24 um.
VARIANT = os.environ.get("SMH_RP", "rp1")
LAND = V.format("smh_tr_group_land_ref", "ot_smh_tr_group_land")
if VARIANT == "rp3":
    # rp3 (21:06 verdict: rp1 18,690 sinks > 15k): rp1 channel and height, the two CLOSED landing masters at the channel
    # edges (W part), both beat_e masters moved E by 8.64 (tile +8.64 wide) so landings and beats share the channel
    # height; per bin bit ONE horizontal trunk (pin reg -> transit) with vertical drops to the landing d faces.
    VIEWS["land"] = LAND
    DIM["land"] = lef_size(LAND)
    W = 406.08
    Y_LAND_S, Y_BEAT, Y_LAND_N, Y_XS0, H = 492.48, 492.48, 665.28, 734.4, 1192.32
    X_LAND = 25.92
elif VARIANT == "rp2":
    VIEWS["land"] = LAND
    DIM["land"] = lef_size(LAND)
    Y_LAND_S, Y_BEAT, Y_LAND_N, Y_XS0, H = 492.48, 561.6, 803.52, 872.64, 1330.56
    X_LAND = 69.12                         # land q (x 8.7-207.3) centred under the xs bk1 face (x 0.7-300.9)
else:
    Y_BEAT = 492.48
    Y_XS0 = 734.4                          # channel top = xs0 bottom (channel 265.68 um)
    H = 1192.32                            # tcl0 top 1,166.4 + 25.92 (138 x 8.64)
DY0 = round(Y_XS0 - 734.4, 3)              # leaf-0 shift vs rp1
BEAT_W = DIM["beat"][0]
X_BEATE = round(W - 69.12, 3)              # E beat stage (bout launch), 23.76 um from the E core edge
X_TRANSIT = round(X_BEATE - 69.12, 3)      # W transit (2 edges) beside it, 25.92-um channel


def children():
    """[(kind, inst glob, x, y, w, h, orient)] eg placement"""
    out = []
    for kind, inst, dx, dy in LEAF0:
        w, h = DIM[kind]
        out.append((kind, f"*g_lf?0?.u_lh.{inst}", round(X0 + dx, 3), round(Y_XS0 + dy, 3), w, h, "R0"))
    for kind, inst, dx, y, o in LEAF1:
        w, h = DIM[kind]
        out.append((kind, f"*g_lf?1?.u_lh.{inst}", round(X0 + dx, 3), y, w, h, o))
    if VARIANT in ("rp2", "rp3"):
        lw, lh = DIM["land"]
        out.append(("land", "*u_ptw.u_groups.u_land_s", X_LAND, Y_LAND_S, lw, lh, "MX"))
        out.append(("land", "*u_ptw.u_groups.u_land_n", X_LAND, Y_LAND_N, lw, lh, "R0"))
    bw, bh = DIM["beat"]
    out.append(("beat", "*u_ptw.u_groups.u_beat_t", X_TRANSIT, Y_BEAT, bw, bh, "R0"))
    out.append(("beat", "*u_pte.u_groups.u_beat", X_BEATE, Y_BEAT, bw, bh, "R0"))
    return out


def gaps(boxes):
    """min edge-to-edge distance between children whose projections overlap (0 = abut); slivers are 0 < d < 20"""
    res = []
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            ax0, ay0, ax1, ay1 = a[2], a[3], a[2] + a[4], a[3] + a[5]
            bx0, by0, bx1, by1 = b[2], b[3], b[2] + b[4], b[3] + b[5]
            if ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1:
                res.append((-1.0, a[1], b[1]))
                continue
            dx = max(bx0 - ax1, ax0 - bx1); dy = max(by0 - ay1, ay0 - by1)
            if dx < 0 and dy >= 0:
                res.append((round(dy, 3), a[1], b[1]))
            elif dy < 0 and dx >= 0:
                res.append((round(dx, 3), a[1], b[1]))
    return res


def edge_gaps(boxes, w, h):
    return [(round(min(b[2], b[3], w - b[2] - b[4], h - b[3] - b[5]), 3), b[1]) for b in boxes]


if __name__ == "__main__":
    cs = children()
    print(f"tile {VARIANT} {W} x {H} = {W * H / 1e6:.4f} mm2; hard {sum(c[4] * c[5] for c in cs) / 1e6:.4f} mm2")
    for c in cs:
        print(c)
    g = gaps(cs)
    print("min child gap", min(x[0] for x in g), "slivers", [x for x in g if 0 < x[0] < 20])
    print("edge", min(edge_gaps(cs, W, H)))
