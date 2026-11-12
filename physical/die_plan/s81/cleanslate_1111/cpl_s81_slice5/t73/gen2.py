#!/usr/bin/env python3
"""CPL-S81-SLICE-5 t73 ST6 quad form (S81-LEAF-CYC CS_HI/HO_D=GS=1, CS_H_G=4): four 2x2 lane quads E of vn, one quad
hi/ho station site per quad on the vn|g_ln street.  Positions only (lane permutation over identical hcpost cores).
usage: gen2.py BASE_PLAN ST4_POS OUTDIR
writes OUTDIR/t73_pos.json (full delta vs BASE, ST4 moves included), OUTDIR/quad_sites.json {lane: [x, y]}"""
import json, sys, os
T = "ot_s81sl_leaf__t73"
base, st4pos, out = sys.argv[1:4]; os.makedirs(out, exist_ok=True)
t = json.load(open(base))["partition_types"][T]; hc = {h["inst"]: h for h in t["hard_cores"]}
pos = json.load(open(st4pos))[T]                      # ST4: ve_m, vsw, ve_s, vs, rxsf, rxsb, vq
DX = 0.0                                              # ST7: street B kept at 147 um (vn/vq/b0/b1 stay)
LIFT = 86.4                                           # ST7: S landing strip for the ft S windows under ve_m/ve_s
for i in ("u_lf.u_ve.u_m", "u_lf.u_ve.u_s", "u_lf.u_vsw", "u_lf.u_vs", "u_lf.u_rxsf", "u_lf.u_rxsb"):
    pos[i] = [pos[i][0], round(pos[i][1] + LIFT, 3), pos[i][2]]
for i in ("u_lf.u_vn.u_a", "u_lf.u_vn.u_b"):
    o = hc[i]["origin_um"]; pos[i] = [round(o[0] + DX, 3), o[1], hc[i]["orient"]]
vq = pos["u_lf.u_vq"]; pos["u_lf.u_vq"] = [round(vq[0] + DX, 3), vq[1], vq[2]]
for i in ("u_lf.u_vp.u_b0", "u_lf.u_vp.u_b1"):
    o = hc[i]["origin_um"]; pos[i] = [round(o[0] + DX, 3), o[1], hc[i]["orient"]]
C1, C2, Y0, P, SX = 1166.4, 1321.92, 8.64, 155.52, 1145.88
vnE = pos["u_lf.u_vn.u_a"][0] + 356.4
vn_mid = (hc["u_lf.u_vn.u_b"]["origin_um"][1] + hc["u_lf.u_vn.u_a"]["origin_um"][1] + 164.16) / 2
sites = {}
for g in range(4):                                    # quad g = lanes 4g..4g+3 (u_vp.g_hig[g] / g_hog[g])
    rows = (Y0 + 2 * g * P, Y0 + (2 * g + 1) * P)
    for j, l in enumerate(range(4 * g, 4 * g + 4)):
        x = (C1, C2)[j % 2]; y = rows[j // 2]
        o = hc[f"u_lf.u_vp.g_ln[{l}].u_l"]["orient"]
        pos[f"u_lf.u_vp.g_ln[{l}].u_l"] = [x, round(y, 3), o]
    cy = rows[0] + (P + 114.48) / 2
    sy = cy + max(-60.0, min(60.0, vn_mid - cy))      # pulled toward vn, quad->lane stays < 405
    for l in range(4 * g, 4 * g + 4): sites[l] = [SX, round(round(sy / 0.27) * 0.27, 3)]
json.dump({T: pos}, open(f"{out}/t73_pos.json", "w"), indent=1)
json.dump(sites, open(f"{out}/quad_sites.json", "w"), indent=1)
# reach (LEAF-CYC criteria): vn pin -> quad <= 810 (through the vp glue flop), quad -> lane W pin <= 405
d = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
vnp = [(vnE, hc["u_lf.u_vn.u_a"]["origin_um"][1] + 85), (vnE, hc["u_lf.u_vn.u_b"]["origin_um"][1] + 86)]
print("vn->quad max", round(max(d(v, s) for v in vnp for s in sites.values()), 1),
      "quad->lane max", round(max(d(sites[l], (pos[f"u_lf.u_vp.g_ln[{l}].u_l"][0], pos[f"u_lf.u_vp.g_ln[{l}].u_l"][1] + 57)) for l in range(16)), 1))
