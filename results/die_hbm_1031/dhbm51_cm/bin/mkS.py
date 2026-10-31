#!/usr/bin/env python3
"""DIE-HBM-49 10-31: static SRAM sites (S.json) for the kit-wave macro items. Names = yosys flatten of the kit RTL
(flat/*.tsv).  y on 0.012 mod 0.048 (M4 track), x on the 0.048 grid; channels >= 10.8 (+0.048 margin)."""
import json, math, sys
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/die-hbm-49/physical/die_plan/hbm")
import core_macros_fix as F
SZ = F.lef_sizes("/srv/opentallas-scratch2/claude/wt/die-hbm-49/physical/asap7_memory_macros_v2")
CM = json.load(open("/srv/opentallas-scratch2/claude/die-hbm-48/kits/plan_d44f_cm/core_macros.json"))["cores"]
G, O = 0.048, 0.012
def yu(v): return round(O + math.ceil(round((v - O) / G, 6)) * G, 3)
def yd(v): return round(O + math.floor(round((v - O) / G, 6)) * G, 3)
def xu(v): return round(math.ceil(round(v / G, 6)) * G, 3)
def xd(v): return round(math.floor(round(v / G, 6)) * G, 3)
def W(m): return SZ[m][0]
def H(m): return SZ[m][1]
S = {}
def put(core, basis, rows, why):
    S[core] = dict(basis=basis, outline_um=CM[core]["outline_um"], macros=[
        dict(name=n, master=m, origin_um=[round(x, 3), round(y, 3)], orient="R0") for n, m, x, y in rows])
def stack_up(items, x, y0, gap=G):
    """items [(name, master)] bottom->top from y0 (snapped up); returns rows, top"""
    rows, y = [], yu(y0)
    for n, m in items:
        rows.append((n, m, x, y)); y = yu(y + H(m) + gap)
    return rows, rows[-1][3] + H(rows[-1][1])
def stack_dn(items, x, ytop, gap=G):
    """items [(name, master)] top->bottom, top macro top edge <= ytop"""
    rows, t = [], ytop
    for n, m in items:
        y = yd(t - H(m)); rows.append((n, m, x, y)); t = y - gap
    return rows
B = "DIE-HBM-49 10-31 static sites (OWNER 07:1x one-block plan event, KIT-WAVE PLAN_CORE_MACROS / macro_channels): "
R128, R256, L64, M64, C32, V1K = ("ot_sram_1r1w_128x256_m1_r2c2", "ot_sram_1r1w_256x256_m2_r2c2", "ot_sram_1r1w_64x512_m1_r2c2",
                                  "ot_sram_1rw_256x64_m4_r2c2", "ot_sram_1r1w2c_32x64_m1", "ot_sram_1r1w_1024x256_m2_r2c2")
HALO = 4.32
# ---------------- (a) host_program 207.36x129.6: 2 x 172.824x41.064, island [99.36,60.48,108,69.12]; pins N+S full width
x = xd((207.36 - W(R256)) / 2)
lo = stack_dn([("u_fcore.provider.lo", R256)], x, 60.48 - 2.16)
hi, _ = stack_up([("u_fcore.provider.hi", R256)], x, 69.12 + 2.16)
put("ot_hnx_fused_host_program", B + "2 SRAMs u_fcore.provider.lo/hi (yosys flatten of view @65a08f6d43f9 kit RTL); one centred column "
    "(W/E channels ~12.9), lo below / hi above the centre clock island [99.36,60.48,108,69.12] which sits in the 12.98-um interior "
    "channel (2.17 um clear each side); N/S pin faces keep ~12.9-um std-cell bands; E/W faces have no pins", lo + hi, "")
# ---------------- (a) hub_n4ext 216x207.36: u_scb + u_pad.u_d (94.824x41.064) + u_pad.u_c (31.992x17.304); island [103.68,99.36,112.32,108]
x = xd((216 - W(R128)) / 2)
lo = stack_dn([("u_fcore.u_native.u_scb", R128)], x, 99.36 - HALO)
up, top = stack_up([("u_fcore.u_native.u_t5.u_pad.u_d", R128)], x, 108 + HALO)
xc = xd(x + (W(R128) - W(C32)) / 2)
up2, top2 = stack_up([("u_fcore.u_native.u_t5.u_pad.u_c", C32)], xc, top + 10.848)
put("ot_hnx_fused_hub_n4ext", B + "3 SRAMs u_fcore.u_native.u_scb / u_t5.u_pad.u_d / u_t5.u_pad.u_c (yosys flatten of view @e84ee0e98a3b "
    "kit RTL); one centred column (W/E channels ~56 = E/W pin-face bands), u_scb below and u_pad.u_d above the centre clock island "
    "[103.68,99.36,112.32,108] (island + 4.32 halo in the interior channel), pad control ring u_c above u_d; S pin face band ~49 um",
    lo + up + up2, "")
# ---------------- (a) tnode 172.8x172.8: u_pad.u_d + u_pad.u_c; island [82.08,82.08,90.72,90.72]; pins W/E full height, N 8, S none
x = xd((172.8 - W(R128)) / 2)
d, top = stack_up([("u_fcore.u_pad.u_d", R128)], x, 15.12)
c, _ = stack_up([("u_fcore.u_pad.u_c", C32)], x, top + 10.848)
put("ot_hnx_fused_tnode", B + "2 SRAMs u_fcore.u_pad.u_d / u_pad.u_c (yosys flatten of view @50055cbac918 kit RTL); one column centred "
    "in x (W/E channels ~34.7 for the W/E pin faces) in the S half (S face has no pins); u_c at the column W end above u_d "
    "(interior channel 10.85), clear of the centre clock island [82.08,82.08,90.72,90.72] by >= 6.8 um", d + c, "")
# ---------------- (a) coll_q2n2_body_core 786.24x743.04: 19 SRAMs; island [388.8,367.2,397.44,375.84]; pins all faces
iss = "u_fcore.u_x.u_body.g_iss256.u_issuer."
lnk = "u_fcore.u_x.u_body.g_link[%d].u_link.g_bank[%d].u_store.u_native.u_sram"
xi = xd(393.12 - W(R256) / 2)
xm = xd(xi + (W(R256) - W(M64)) / 2)
lo = stack_dn([(iss + "g_mem[0].u_bank.u_sram_hi", R256), (iss + "g_mem[0].u_bank.u_sram_lo", R256)], xi, 367.2 - HALO)
lo2 = stack_dn([(iss + "g_meta[1].u_sram", M64), (iss + "g_meta[0].u_sram", M64)], xm, lo[-1][3] - G)
up, t = stack_up([(iss + "g_mem[1].u_bank.u_sram_lo", R256), (iss + "g_mem[1].u_bank.u_sram_hi", R256),
                  (iss + "g_mem[2].u_bank.u_sram_lo", R256), (iss + "g_mem[2].u_bank.u_sram_hi", R256)], xi, 375.84 + HALO)
up2, t2 = stack_up([(iss + "g_meta[2].u_sram", M64), (iss + "g_meta[3].u_sram", M64),
                    ("u_fcore.u_x.u_body.g_q2.n_u_fj.u_fj.u.u_program.g_fsram.u_flow", M64)], xm, t + G)
gapc = 59.808
xl0 = xd(xi - gapc - W(L64)); xl1 = xu(xi + W(R256) + gapc)
links = []
for L, xl in ((0, xl0), (1, xl1)):
    hgt = 4 * H(L64) + 2 * G + 10.848
    r1, tt = stack_up([(lnk % (L, 0), L64), (lnk % (L, 1), L64)], xl, 371.52 - hgt / 2)
    r2, _ = stack_up([(lnk % (L, 2), L64), (lnk % (L, 3), L64)], xl, tt + 10.848)
    links += r1 + r2
put("ot_hfd_coll_q2n2_body_core", B + "19 SRAMs (yosys flatten of view @c98dcf9c336e kit RTL: issuer g_mem[0..2] lo/hi 256x256, "
    "g_meta[0..3] + g_q2 u_flow 1rw_256x64, g_link[0..1] g_bank[0..3] 64x512); 3 centre columns: issuer column centred on the "
    "clock entry x 393.12 (mem0 pair + meta0/1 below, mem1/mem2 pairs + meta2/3 + u_flow above the island "
    "[388.8,367.2,397.44,375.84] which sits with 4.32 halo in the interior channel), link0 / link1 columns W / E of it "
    "(2+2 stack, 10.85 interior channel, centred on y 371.52); ~60-um inner channels, ~71-um W/E and >=140-um N/S std-cell "
    "bands for the 12k-pin faces", lo + lo2 + up + up2 + links, "")
# ---------------- (b) pslice_c5 939.6x760.32: keep the 8x13 grid, x pitch 116.64 -> 116.304 from x0 15.168, rows 7..12 +10.56
old = CM["ot_hbm_su_programme_pslice_c5"]["macros"]
cx = sorted({r["rect_um"][0] for r in old}); ry = sorted({r["rect_um"][1] for r in old})
rows = []
for r in old:
    i, j = cx.index(r["rect_um"][0]), ry.index(r["rect_um"][1])
    rows.append((r["name"], r["master"], 15.168 + i * 116.304, r["rect_um"][1] + (10.56 if j >= 7 else 0.0)))
put("ot_hbm_su_programme_pslice_c5", B + "re-site of the d44g KNOWN explicit grid (same 100 names/masters, 8 columns x 13 rows): "
    "column pitch 116.64 -> 116.304 from x0 12.96 -> 15.168 (W channel 8.64 -> 10.85, E 11.02 -> 11.16, inner 21.48; clock "
    "island [466.56,375.84,475.2,384.48] + 4.32 halo stays in the column 3/4 channel); rows 7..12 shifted +10.56 so every "
    "column has an interior horizontal channel 10.81 (was 13 abutted, gap 0.246)", rows, "")
# ---------------- (b) xload_cl2_bfqg: column 1 (g_t[4], g_t[7]) +2.208 -> W channel 10.848
old = CM["ot_hgi_sm_xload_cl2_bfqg"]["macros"]
rows = [(r["name"], r["master"], r["rect_um"][0] + (2.208 if r["rect_um"][0] > 100 else 0),
         yu(r["rect_um"][1] + 10.8) if r["name"] == "u_fcore.g_t[7].u_m" else r["rect_um"][1]) for r in old]
put("ot_hgi_sm_xload_cl2_bfqg", B + "re-site of the d44g KNOWN placed rects (same 8 names): column 1 (g_t[4], g_t[7]) moved "
    "+2.208 um in x so the column 0/1 channel is 10.848 (was 8.64) and g_t[7] +10.8 um in y so column 1 has a "
    "10.8+ interior channel (was abutted, 0.024); all else unchanged; clock island [146.88,142.56,155.52,151.2] clear "
    "(column 1 ends at y 110.3)", rows, "")
# ---------------- (3) keybuf_slice: 5 stacked 172.824x41.064 (plan rects used 172.8x41.04) -> pitch 51.888
old = sorted(CM["ot_hnx_idxn_keybuf_slice"]["macros"], key=lambda r: r["rect_um"][1])
rows = [(r["name"], r["master"], r["rect_um"][0], 15.12 + k * 51.888) for k, r in enumerate(old)]
put("ot_hnx_idxn_keybuf_slice", B + "re-site of the d44g KNOWN explicit stack (same 5 names u_fcore.gm[0..4].mem): the plan "
    "rects used 172.8x41.04 but the LEF is 172.824x41.064 so the stacked gaps were 10.776; y pitch 51.84 -> 51.888 (gaps "
    "10.824), x unchanged; clock island [203.04,142.56,211.68,151.2] clear (column ends at x 197.664)", rows, "")
# ---------------- (1) lane_exp canon 440.64x207.36: 3 cols x 2 rows; island [216,99.36,224.64,108] in col 1 interior channel
old = CM["ot_hbm_su_static_pgslice_lg__lane_exp__canon_7cd691"]["macros"]
x1 = xd(220.32 - W(R128) / 2); xs = [xd(x1 - 10.848 - W(R128)), x1, xu(x1 + W(R128) + 10.848)]
ylo = yd(99.36 - HALO - H(R128)); yhi = yu(108 + HALO)
cxo = sorted({r["rect_um"][0] for r in old})
rows = [(r["name"], r["master"], xs[cxo.index(r["rect_um"][0])], ylo if r["rect_um"][1] < 100 else yhi) for r in old]
put("ot_hbm_su_static_pgslice_lg__lane_exp__canon_7cd691", B + "re-site of the d44g KNOWN rects (same 6 names g_read[0..5], "
    "3 columns x 2 rows): column 1 centred on the clock entry x 220.32, inner channels 8.856 -> 10.848 (W/E bands ~62.9), "
    "rows split around the clock island [216,99.36,224.64,108] + 4.32 halo (interior channel 9.05 -> 17.3); N/S bands ~49.6", rows, "")
# ---------------- (2) lanes canon 760.32x725.76: 24 SRAMs u_bank[0..3] g_read[0..5] -> 4 bank columns 3+3, island in col1/col2 channel
old = CM["ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77"]["macros"]
G2 = 21.6
x1r = xd(380.16 - G2 / 2); x1 = xd(x1r - W(R128)); xs = [xd(x1 - G2 - W(R128)), x1, xu(x1r + G2), 0]
xs[3] = xu(xs[2] + W(R128) + G2)
hgt = 6 * H(R128) + 4 * G + 10.848
rows = []
for b in range(4):
    nm = lambda k: f"u_fcore.u_core.u_bank{b}.u_data.g_read[{k}].u_m"
    r1, t = stack_up([(nm(k), R128) for k in range(3)], xs[b], 362.88 - hgt / 2)
    r2, _ = stack_up([(nm(k), R128) for k in range(3, 6)], xs[b], t + 10.848)
    rows += r1 + r2
assert {r[0] for r in rows} == {r["name"] for r in old}, "lanes names"
put("ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77", B + "re-site of the d44g KNOWN placed rects (same 24 names "
    "u_bank[0..3].u_data.g_read[0..5].u_m; the RTL-MP form had 8.64 column channels and 0.024-0.072 stacked gaps): one column "
    "per bank (g_read 0..2 below / 3..5 above a 10.85 interior channel), 21.6 inner channels with the clock island "
    "[375.84,358.56,384.48,367.2] centred in the bank1/bank2 channel, block centred on the entry (W/E/N/S bands >= 150 um)", rows, "")
# ---------------- (4) vms_bank_q0_faces vec6293 (4) / vecd4ae (3): 174.744x70.488; island [129.6,151.2,138.24,159.84]
for mod, names, view in (("hnx_vms_bank_q0_faces__vec6293", ["u_a", "u_b", "u_c", "u_h"], "@d2ac2d17712e/@f50d62432a5f"),
                         ("hnx_vms_bank_q0_faces__vecd4ae", ["u_a", "u_b", "u_c"],
                          "@114e9076fa98/@d6532bde006e/@ed4cba8a8b2a/@f9c1bd05a046")):
    p = "u_fcore.u_core.u_ot_pr_core.bank."
    x = xd((270 - W(V1K)) / 2)
    lo = stack_dn([(p + names[0], V1K)], x, 151.2 - HALO)
    up, _ = stack_up([(p + n, V1K) for n in names[1:]], x, 159.84 + HALO)
    jn = "/".join(names)
    put(mod, B + f"{len(names)} SRAMs {jn} (yosys flatten of views {view} kit RTL, all pin tables) 1r1w_1024x256: "
        "one centred column (W/E channels ~43.3), bank.{0} below and the rest above the clock island [129.6,151.2,138.24,159.84] "
        "(+4.32 halo in the interior channel); the S face carries the most pins in every table so the column leans N".format(names[0]),
        lo + up, "")
json.dump(S, open(sys.argv[1], "w"), indent=1)
for c, s in S.items():
    rr = [dict(name=m["name"], master=m["master"], orient="R0", rect_um=[m["origin_um"][0], m["origin_um"][1],
          m["origin_um"][0] + W(m["master"]), m["origin_um"][1] + H(m["master"])]) for m in s["macros"]]
    err, nc = F.channel_errors(rr, s["outline_um"])
    print(c, len(rr), "cols", nc, "ERR" if err else "ok", err[:3])
