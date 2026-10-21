"""S81-SLICE/ENDP 10-21: shared geometry + landed-region plan of the four selected72 MU end parents (LANDED REGIONS).

Regions (every crossing a fixed-latency D4 landing ring, chunk 8, kept-enable writer; no reset root: one regional reset
port per region, fixed-depth forest on the region's own clock):
  S   u_sl  (c1x_k8_cap5r_lp; its own ck_C = ck_S, the other nine real roots ck_L0..ck_CAP_RS pass straight to u_sl)
  K   u_lep + lanes (lanes ABUT the endpoint lane face, 51.84 um gap: same region, direct, owner 10-20 09:05 rule)
  ML  u_land (dsdv_mu_land SRAM 1)
  P   port-entry region (no child): the small die control ports (mu_c / mu_rc / mu_rt / fault, + host ports on lepe_mu) land
      at the parent face and cross to K / ML in rings, so the ~1.3-1.6 mm face->endpoint run is a ring bank wire (multicycle
      E T), never a single-cycle wire.
MAIN = E 2 (rings +3 edges).  FALLBACK = E 3 (rings +4 edges: 3 T bank reach for the P runs) + wider line channel / slot.
"""
H = 6825.6
SL_W, SL_H = 1252.8, 6739.2
LANE_W, LANE_H = 725.76, 583.2
LAND_W, LAND_H = 475.2, 216.0
LEP = {"lepw_mab_mu": ("ot_s81sl_lep_mu_ab", 475.2, 1900.8), "lepw_mu": ("ot_s81sl_lep_mu_a", 561.6, 518.4),
       "lepe_mu": ("ot_s81sl_lep_mu_h", 561.6, 518.4), "lepe_nh_mu": ("ot_s81sl_lep_mu_a", 561.6, 518.4)}
SID = {"lepw_mab_mu": "4'd1", "lepw_mu": "4'd0", "lepe_mu": "4'd15", "lepe_nh_mu": "4'd14"}   # s_0N / s_0S / s_7N / s_7S
HOST = ["t_host", "t_kd", "f_host", "f_lf", "f_ks"]


def geom(f, v):
    """v 'a' = MAIN (E 2), 'b' = FALLBACK (E 3, slot +172.8 into the line channel)."""
    lep, lw, lh = LEP[f]
    W = 2851.2 if v == "a" else 3024.0
    ch = (259.2 if f == "lepw_mab_mu" else 172.8) + (0 if v == "a" else 172.8)
    g = dict(f=f, v=v, W=W, H=H, ch=ch, lep=lep, lep_w=lw, lep_h=lh, E=2 if v == "a" else 3,
             side="w" if f.startswith("lepw") else "e")
    if g["side"] == "w":
        g["sl"] = (round(W - 43.2 - SL_W, 3), 43.2)
        lep_x = round(g["sl"][0] - ch - lw, 3)
        g["lane_x"] = 43.2
        g["lep_orient"] = "R0"
    else:
        g["sl"] = (43.2, 43.2)
        lep_x = round(43.2 + SL_W + ch, 3)
        g["lane_x"] = round(lep_x + lw + 51.84, 3)
        g["lep_orient"] = "MY"
    if f == "lepw_mab_mu":
        lep_y = 1728.0
        g["lanes"] = [1490.4, 2116.8, 2743.2, 3369.6]
        g["pstreet"] = (3326.4, 3369.6)                     # 43.2 gap ln2 / ln3: P ports (W face)
    else:
        lep_y = 2592.0
        g["lanes"] = [2246.4, 2937.6]                       # street 108 between them (centre 2883.6 ~ lep centre)
        g["pstreet"] = (2829.6, 2937.6)
    g["lep_xy"] = (lep_x, lep_y)
    g["land_xy"] = (lep_x if g["side"] == "w" else lep_x, round(lep_y + lh + 259.2 if f == "lepw_mab_mu" else lep_y + lh + 172.8, 3))
    if g["lane_x"] + LANE_W > W - 43.2 + 1e-6 and g["side"] == "e":
        raise SystemExit(f"{f}{v}: lanes overrun the E face")
    sx = g["sl"][0]
    g["centre"] = {"S": [round(sx + SL_W / 2, 1), 2894.4], "K": [round(lep_x + lw / 2, 1), round(lep_y + lh / 2, 1)],
                   "ML": [round(lep_x + LAND_W / 2, 1), round(g["land_xy"][1] + LAND_H / 2, 1)],
                   "P": [20.0 if g["side"] == "w" else round(W - 20, 1), round(sum(g["pstreet"]) / 2, 1)]}
    return g
