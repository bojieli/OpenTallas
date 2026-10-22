#!/usr/bin/env python3
"""STW-S81c-COLLA3-LEP 10-22 (lep_mu_h w14): station plan for physical/common_flow/relay_chain_place.tcl (OT_RELAY_HIER=1).

  relay_plan.py GEOM.json F_RELAY F_SEL > relay_place.txt

GEOM.json = pin / RX-macro geometry of the 648 x 604.8 lattice (r7m / c12m: same pins, outline and macro sites), taken from
the r7m --cts gate dump (ml_wd[*] / ri[*] pin centres, RX bank rd_out pin column).
  * WRLY relay byte ob (u_ot_pr_core.u.g_rxm.g_ml_nface_out[ob].u_relay): placed at F_RELAY of the way from its RX bank's
    rd_out pin column (lane 0 = rb[551:0], lane 1 = rb[1103:552], bank = lane bit / 128) to the centre of its 8 ml_wd pins.
  * delivery-select owner c (u_ot_pr_core.u.g_rxm.g_o[c].g_on.g_registered_select.u_sel, rid bits 1+16c .. 16+16c):
    x = F_SEL * outline width (between rx_control's W-face sources and the E-face rid owners), y = its ri pins' centre.
"""
import json, sys
g = json.load(open(sys.argv[1])); fr = float(sys.argv[2]); fs = float(sys.argv[3])
W = 648.0
pins = g["pins"]; mac = g["macros"]
def bank_src(lane, bank):
    m = mac[f"u_ot_pr_core.u.g_rx[{lane}].g_sa.g_true_sram.u_rx_mem.g_bank[{bank}].u_m"]
    return m["out_x"], sum(m["out_y"]) / 2
out = [f"# relay_plan.py F_RELAY {fr} F_SEL {fs}: 138 WRLY relay bytes + 69 select owners"]
mx = 0
for ob in range(138):
    bits = range(8 * ob, 8 * ob + 8)
    lane = 0 if ob < 69 else 1
    lb = 8 * ob - 552 * lane
    sx, sy = bank_src(lane, lb // 128)
    px = sum(pins[f"ml_wd[{b}]"][0] for b in bits) / 8; py = sum(pins[f"ml_wd[{b}]"][1] for b in bits) / 8
    x = sx + fr * (px - sx); y = sy + fr * (py - sy)
    d1 = abs(x - sx) + abs(y - sy); d2 = abs(px - x) + abs(py - y); mx = max(mx, d1, d2)
    out.append(f"u_ot_pr_core.u.g_rxm.g_ml_nface_out[{ob}].u_relay {x:.2f} {y:.2f} wrly_d1_{d1:.0f}_d2_{d2:.0f}")
for c in range(69):
    lo, hi = 1 + 16 * c, min(1104, 1 + 16 * (c + 1))
    py = sum(pins[f"ri[{b}]"][1] for b in range(lo, hi)) / (hi - lo)
    out.append(f"u_ot_pr_core.u.g_rxm.g_o[{c}].g_on.g_registered_select.u_sel {fs * W:.2f} {py:.2f} sel")
print("\n".join(out))
print(f"# max WRLY hop {mx:.0f} um", file=sys.stderr)
