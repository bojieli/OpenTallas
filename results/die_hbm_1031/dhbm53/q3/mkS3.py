#!/usr/bin/env python3
"""DIE-HBM-53 10-31: static SRAM sites (S.json) for the q3 coll cores (body/edge).  Names = yosys flatten of the probe kit
RTL (q3/flat/*.tsv).  Same arithmetic as DIE-HBM-49 mkS.py: y on 0.012 mod 0.048, x on 0.048, channels >= 10.8."""
import json, math, sys
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/die-hbm-49/physical/die_plan/hbm")
import core_macros_fix as F
SZ = F.lef_sizes("/srv/opentallas-scratch2/claude/wt/die-hbm-49/physical/asap7_memory_macros_v2")
CM = json.load(open("/srv/opentallas-scratch2/claude/die-hbm-49/macros/plan_cm/core_macros.json"))["cores"]
G, O, HALO = 0.048, 0.012, 4.32
yu = lambda v: round(O + math.ceil(round((v - O) / G, 6)) * G, 3)
yd = lambda v: round(O + math.floor(round((v - O) / G, 6)) * G, 3)
xd = lambda v: round(math.floor(round(v / G, 6)) * G, 3)
W = lambda m: SZ[m][0]
H = lambda m: SZ[m][1]
def stack_up(items, x, y0, gaps=None):
    rows, y = [], yu(y0)
    for i, (n, m) in enumerate(items):
        rows.append((n, m, x, y)); y = yu(y + H(m) + (gaps[i] if gaps else G))
    return rows, rows[-1][3] + H(rows[-1][1])
def stack_dn(items, x, ytop, gaps=None):
    rows, t = [], ytop
    for i, (n, m) in enumerate(items):
        y = yd(t - H(m)); rows.append((n, m, x, y)); t = y - (gaps[i] if gaps else G)
    return rows
S = {}
B = "DIE-HBM-53 10-31 static sites (OWNER 07:1x one-block NO_RECIPE plan event, q3 coll cores PLAN_CORE_MACROS): "
def put(core, basis, rows):
    S[core] = dict(basis=basis, outline_um=CM[core]["outline_um"], macros=[
        dict(name=n, master=m, origin_um=[round(x, 3), round(y, 3)], orient="R0") for n, m, x, y in rows])
R256, M64, L64 = "ot_sram_1r1w_256x256_m2_r2c2", "ot_sram_1rw_256x64_m4_r2c2", "ot_sram_1r1w_64x512_m1_r2c2"
# ---- body 578.88x1054.08: 11 SRAMs; island [285.12,522.72,293.76,531.36]; pins N 5792 / E 4683 / S 2964 / W 2544
iss = "u_fcore.u_core.u_x.u_body.g_iss256.u_issuer."
xi = xd(289.44 - W(R256) / 2); xm = xd(xi + (W(R256) - W(M64)) / 2)
lo = stack_dn([(iss + "g_mem[0].u_bank.u_sram_hi", R256), (iss + "g_mem[0].u_bank.u_sram_lo", R256)], xi, 522.72 - HALO)
lo2 = stack_dn([(iss + "g_meta[1].u_sram", M64), (iss + "g_meta[0].u_sram", M64)], xm, lo[-1][3] - G)
up, t = stack_up([(iss + "g_mem[1].u_bank.u_sram_lo", R256), (iss + "g_mem[1].u_bank.u_sram_hi", R256),
                  (iss + "g_mem[2].u_bank.u_sram_lo", R256), (iss + "g_mem[2].u_bank.u_sram_hi", R256)], xi, 531.36 + HALO)
up2, _ = stack_up([(iss + "g_meta[2].u_sram", M64), (iss + "g_meta[3].u_sram", M64),
                   ("u_fcore.u_core.u_x.u_body.g_q3.n_u_fj.u_fj.u.u_program.g_fsram.u_flow", M64)], xm, t + G)
put("ot_hfd_coll_q3_body_core", B + "11 SRAMs (yosys flatten of view @e9fac1f891ac kit RTL: issuer g_mem[0..2] lo/hi 256x256, "
    "g_meta[0..3] + g_q3 u_flow 1rw_256x64) = the q2n2 body issuer column (DIE-HBM-49 site form) without the link banks: one "
    "column centred on the clock entry x 289.44, mem0 pair + meta0/1 below and mem1/mem2 pairs + meta2/3 + u_flow above the "
    "island [285.12,522.72,293.76,531.36] (+4.32 halo in the interior channel); W/E std-cell bands ~203 um, N band ~300 um "
    "for the 5.8k-pin N face", lo + lo2 + up + up2)
# ---- edge 216x1054.08: 12 x 64x512 u_link0..2 g_bank[0..3]; island [103.68,522.72,112.32,531.36]; pins W/E only
nm = lambda L, b: f"u_fcore.u_core.u_link{L}.g_bank[{b}].u_store.u_native.u_sram"
items = [(nm(L, b), L64) for L in range(3) for b in range(4)]
x = xd((216 - W(L64)) / 2)
gp = [G, 10.848, G, 10.848, G, 0]
lo = stack_dn(list(reversed(items[:6])), x, 522.72 - HALO, gaps=gp)
up, _ = stack_up(items[6:], x, 531.36 + HALO, gaps=gp)
put("ot_hfd_coll_q3_edge_core", B + "12 SRAMs 1r1w_64x512 u_link0..2.g_bank[0..3] (yosys flatten of view @9bacba9ba155 kit "
    "RTL) = the r15 k3m single centred column (W/E bands ~22.4 for the W/E pin faces; N/S faces have no pins); link0/link1.b0-1 "
    "below and link1.b2-3/link2 above the clock island [103.68,522.72,112.32,531.36] (+4.32 halo), stacked in abutted pairs "
    "(0.048) with 10.848 channels between pairs", lo + up)
json.dump(S, open(sys.argv[1], "w"), indent=1)
for c, s in S.items():
    rr = [dict(name=m["name"], master=m["master"], orient="R0", rect_um=[m["origin_um"][0], m["origin_um"][1],
          m["origin_um"][0] + W(m["master"]), m["origin_um"][1] + H(m["master"])]) for m in s["macros"]]
    err, nc = F.channel_errors(rr, s["outline_um"])
    ys = sorted(r["rect_um"][1] for r in rr); ye = max(r["rect_um"][3] for r in rr)
    print(c, len(rr), "cols", nc, "ERR" if err else "ok", err[:3], "y", ys[0], ye)
