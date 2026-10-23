#!/usr/bin/env python3
"""STW-S81c-COLLA3-LEP2 10-22 (lep_mu_h w15): TX macro-face capture stations for relay_chain_place.tcl (re: keys).

  station_plan.py BASE_relay_place.txt m|f > relay_place.txt

w14m --cts gate (4_1_cts ODB, TT placement RC), the two rejected classes:
  (a) macro->reg -164.7: TX lane-1 bank-0 rd_out[79] (W face 302.4,52.6) -> g_rp.odr[79] placed at (379.8,288.2); the
      q mux (select_r ? forwarded : raw) at (403.1,512.9): 313 um Manhattan + a 460-um detour.  odr of every TX bank is
      spread 150-490 um from its macro (t1 bank0 y 92..583).
  (b) reg->reg -124.5: PUSHREP replica g_slice[4] ph (494.5,112.5) -> u_push (494.9,114) -> push_group[8] -> one ABC
      inverter shared by both lanes placed at the TX0 face (27,152) -> back to TX1 g_address[4].wp_r[8] (284.6,145.9);
      TX0 g_address[5] sat at (15,351), 200 um from its bank.
Plan (no RTL / latency change): per TX lane t, bank b (macro W face xf = 43.2 / 302.4, y0 = 43.2 + 86.4 b, rd_out pins
y0+1.8..y0+14.0, inputs y0+0.8..y0+21.7)
  DATA box  odr[128b..128b+127] + u_m.g_slice[16b..16b+15].{forwarded,select_r,valid_r,addr_r}  at the rd_out pins
  ADDR box  g_address[4b..4b+3].{wp_r,rp_r,count_r,credit_r} + u_m.g_address[..].{address_r,valid_r} above it
  PUSH      replica g_slice[c].g_rep.u_rep + g_push_groups.g_group[c].{u_push,ring_r} (c = 4b..4b+3) in the TX0|TX1
            channel (x 228-292) at the bank row, y capped so the status->replica leg stays <= ~560 um.
Cells are FIRM through global placement and released before DPL (relay_chain_release.tcl).
"""
import sys

base, mode = sys.argv[1], sys.argv[2]
HALO = 12.8
XF = {0: 43.2, 1: 302.4}
NG, NBANK, H1 = 18, 5, 553          # address groups, banks, word bits (H+1)
out = [l.rstrip("\n") for l in open(base)]
out.append(f"# station_plan.py {mode}: TX macro-face DATA / ADDR boxes + push stations (STW-S81c-COLLA3-LEP2)")


def alt(lo, hi):
    return "(" + "|".join(str(i) for i in range(lo, hi)) + ")"


for t in (0, 1):
    xf = XF[t]
    x1 = xf - HALO
    if mode == "m":
        x0 = 11.0 if t == 0 else x1 - 22.0
    else:
        x0 = x1 - 14.0
    for b in range(NBANK):
        y0 = 43.2 + 86.4 * b
        lo, hi = 128 * b, min(H1, 128 * (b + 1))
        s_lo, s_hi = 16 * b, min((H1 + 7) // 8, 16 * (b + 1))
        g_lo, g_hi = 4 * b, min(NG, 4 * (b + 1))
        T = rf"^u_ot_pr_core\.u\.g_tx\[{t}\]\."
        if mode == "m":
            dy0, dy1, ay1 = y0 - 6.0, y0 + 16.0, y0 + 34.0
        else:
            dy0, dy1, ay1 = y0 + 0.5, y0 + 15.5, y0 + 25.0
        # one key (one grid) for the read capture and the q-mux sources, so the two never share box sites
        out.append(f"re:{T}(g_rp\\.odr\\[{alt(lo, hi)}\\]\\$|g_safe_write\\.u_m\\.g_slice\\[{alt(s_lo, s_hi)}\\]\\."
                   f"(forwarded|select_r|valid_r|addr_r)) {x0:.2f} {dy0:.2f} {x1:.2f} {dy1:.2f}")
        out.append(f"re:{T}g_safe_write\\.(u_m\\.)?g_address\\[{alt(g_lo, g_hi)}\\]\\.(wp_r|rp_r|count_r|credit_r\\[|address_r|valid_r) "
                   f"{x0:.2f} {dy1:.2f} {x1:.2f} {ay1:.2f}")
for c in range(NG):
    b = c // 4
    y0 = 43.2 + 86.4 * b
    if mode == "m":
        x, y = 247.0, min(y0 + 10.0, 275.0)
    else:
        x, y = 252.0, min(y0 + 10.0, 230.0)
    out.append(f"u_ot_pr_core.u.g_frame_local.g_slice[{c}].g_rep.u_rep {x:.2f} {y:.2f} push{c}")
    out.append(f"u_ot_pr_core.u.g_push_groups.g_group[{c}].u_push {x:.2f} {y:.2f} push{c}")
    out.append(f"re:^u_ot_pr_core\\.u\\.g_push_groups\\.g_group\\[{c}\\]\\.ring_r {x:.2f} {y:.2f}")
print("\n".join(out))
