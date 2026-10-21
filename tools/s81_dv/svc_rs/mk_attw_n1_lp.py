#!/usr/bin/env python3
"""DRIVE-S81-ATTN1 (10-20, G4 re-plan): the NARROWED attw (engine NTP 1: ONE physical tile = 4 hard head groups) as a
LANDED PARENT (2 regions: c + t0), for the G4 attention slot (Codex G4split112 model 950.4 x 2160).

    python3 tools/s81_dv/svc_rs/mk_attw_n1_lp.py VARIANT [STD_AREA_UM2] [HG_VIEW]
        VARIANT  main: 1036.8 x 2160 -- 2 x 2 groups, channels W 43.2 | centre 86.4 | E 43.2 (the 950.4 model leaves the
                       west group's W pin face (ld_w, 1,024 pins) on the outline edge: unroutable; +86.4 is the minimum)
                 fb:   1123.2 x 2160 -- 2 x 2 groups, 86.4 channels on every side (the proven 4-tile attw spacing)
        -> tools/landed_parent/specs/dsdv_svc_attw_n1_f.json                      (lp.py spec; then lp.py gen it)
           tools/ref_tile/specs_s81dv_svc_lp/dsdv_svc_attw_n1_<variant>_lp.json  (ref_tile kit spec of the landed top)

Flat parent rtl/dsrom_sys/s81_dv/svc_rs/attw/dsdv_svc_attw_n1_f.sv = u_c (dsdv_svc_rs_attw1 TEXT 1 NTP 1) + u_t0
(ot_hdc_v41x_attn_tile_s, -DOT_ATTN_HGRP_HARD -DOT_ATTN_HGRP8: 4 hard s81svc_attn_hgrp8 groups).  The one tile bundle
(1,618 b in, 529 b out) is LANDED both ways: +3 edges each = TLX 6 (as the 4-tile attw).

Floorplan (origin SW, 43.2 lattice), bottom = region c, top = region t0:
    y 1166.4 .. 2116.8: 2 x 2 hgrp8 (432 x 432; group g at column g % 2, row g // 2), rows 86.4 apart (upper S face ib
                        + lower N face controls), 86.4 channel to c below (lower S faces ib), 43.2 top margin;
    y 0 .. 1080: c = 2 big SRAM columns (16 x ot_sram_1r1w_256x256_m2_r2c2 each: landing 12 + p store 4 + staging 16),
                 2 small SRAM columns (19 x ot_sram_1r1w_32x128_m1: wq 12 + sw 5 + qm 4 + pv 17), std cells east of them
                 (and above the stacks); STD_AREA_UM2 sizes nothing here (the band is what is left; the script reports
                 the utilisation the synthesis area implies).
attw ports on N (from the svc_rs slice above: they reach c through the west channel) / S (below, c), clocks ck_c (S
centre of c), ck_t0 (N centre of the tile region).
"""
import json, math, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
VAR = sys.argv[1] if len(sys.argv) > 1 else "main"
A = float(sys.argv[2]) if len(sys.argv) > 2 else 190000.0
HG_VIEW = sys.argv[3] if len(sys.argv) > 3 else "physical/ref_tile/s81svc_attn_hgrp8/views/ot_s81svc8_hgrp_s81_bounded"
assert VAR in ("main", "fb"), VAR
G = 43.2
HG = 432.0
BW_, BH = 172.8, 41.04          # ot_sram_1r1w_256x256_m2_r2c2
SW, SH = 51.408, 20.79          # ot_sram_1r1w_32x128_m1
CH = 2 * G
r3 = lambda v: round(v, 3)
D = "rtl/dsrom_sys/s81_dv/svc_rs"
V = "rtl/hdc/v41x"
SRC = [f"{V}/ot_hdc_v41x_attn_tile_s.sv", f"{V}/ot_hdc_v41x_attn_s.sv",
       f"{V}/ot_hdc_v41x_kreg.sv", f"{V}/ot_hdc_v41x_attn_tile_lat.sv", f"{V}/ot_hdc_v41x_attn_tile.sv",
       f"{V}/ot_hdc_v41x_attn.sv", f"{V}/ot_hdc_v41x_attn_staging.sv",
       "physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v",
       "physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v",
       "rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/ot_hdc_fp32_add_lat.sv", "rtl/hdc/ot_hdc_prefix.sv", "rtl/hdc/ot_hdc_fp32_f12.sv",
       f"{V}/ot_dsrom_su_add6.sv", "rtl/hdc/ot_hdc_delay.sv", "rtl/dsrom_sys/s81_ctrl/ot_s81_svc_job.sv",
       "rtl/hdc/ot_hdc_fastfp_lat_f12.sv", "rtl/hdc/ot_hdc_fp32_mul_lat.sv",
       f"{D}/dsdv_svc_att.sv", f"{D}/dsdv_svc_rs_glue.sv"]
# the hard group: blackboxed by the kit (child view); the lp lockstep bench simulates its RTL (same ports / cycles)
HG_RTL = [f"{V}/ot_s81svc8_hgrp_s81.sv", f"{V}/ot_s81svc8_ring.sv",
          "physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1.v"]
DEFS = ["OT_ATTN_HGRP_HARD", "OT_ATTN_HGRP8", "OT_SVC_LAND_SRAM", "OT_SVC_ATT_SRAM", "OT_SVC_ATT_PINREG"]
PAR = dict(AMUT=0, DIE_ID=0, ST=0, SRAM_MACRO=1, ROOT=0, PMEM=1)

# ------------------------------------------------------------------ geometry
cw, cc, ce = (G, CH, G) if VAR == "main" else (CH, CH, CH)       # W / centre / E channels of the group block
W = r3(cw + HG + cc + HG + ce)
H = 2160.0
xg = [cw, r3(cw + HG + cc)]
yl = r3(H - G - HG - CH - HG)             # lower group row
yu = r3(yl + HG + CH)
yc_top = r3(yl - CH)                      # top of region c
big_n, small_n = 16, 19
bx = [G, r3(G + BW_ + G)]
sx = [r3(bx[1] + BW_ + G), r3(bx[1] + BW_ + G + SW + G)]
std_x0 = r3(math.ceil((sx[1] + SW + G) / G - 1e-9) * G)
by = G
sy = G
ms = []
def stack(view, h, x, y, insts):
    for i, n in enumerate(insts):
        ms.append({"view": f"physical/asap7_memory_macros/{view}", "inst": n, "count": 1,
                   "at": [r3(x), r3(y + i * h)], "orient": "R0" if i % 2 == 0 else "MX"})
stage = [f"*u_stage{s}.g_macro.g_lane?{l}?.g_slice?{k}?.g_256.u_mem" for s in (0, 1) for l in range(4) for k in range(2)]
land = [f"*u_core.g_land?{c}?.g_b?{b}?.u_mem" for b in range(4) for c in range(3)]
pmem = [f"*u_core.g_pmem.g_bank?{b}?.g_half?{h}?.u_mem" for b in range(2) for h in range(2)]
wq = [f"*u_core.g_wqh?{c}?.g_p?{p}?.g_m.u_wqm.g_m?{k}?.u_m" for c in (0, 2) for p in (0, 1) for k in range(3)]
sw = [f"*u_core.u_swm.g_m?{k}?.u_m" for k in range(5)]
qm = [f"*u_core.u_qmm.g_m?{k}?.u_m" for k in range(4)]
pv = [f"*u_core.g_pvq.u_pvm.g_m?{k}?.u_m" for k in range(17)]
big = land + pmem + stage
small = wq + sw + qm + pv
assert len(big) == 32 and len(small) == 38
stack("ot_sram_1r1w_256x256_m2_r2c2", BH, bx[0], by, big[:big_n])
stack("ot_sram_1r1w_256x256_m2_r2c2", BH, bx[1], by, big[big_n:])
stack("ot_sram_1r1w_32x128_m1", SH, sx[0], sy, small[:small_n])
stack("ot_sram_1r1w_32x128_m1", SH, sx[1], sy, small[small_n:])
assert by + big_n * BH < yc_top and sy + small_n * SH < yc_top
ch = [{"view": HG_VIEW, "inst": f"u_t0.g_g?{g}?.u_g", "count": 1,
       "at": [r3(xg[g % 2]), r3(yl if g < 2 else yu)]} for g in range(4)]
c_area = W * yc_top - 32 * BW_ * BH - 38 * SW * SH
std_band = (W - std_x0) * yc_top + std_x0 * (yc_top - max(by + big_n * BH, sy + small_n * SH))
regions = [{"name": "c", "insts": ["u_c"], "centre": [r3(W / 2), r3(yc_top / 2)]},
           {"name": "t0", "insts": ["u_t0"], "centre": [r3(W / 2), r3((yl + yu + HG) / 2)]}]
print(f"attw_n1 {VAR}: outline {W} x {H} = {W * H / 1e6:.3f} mm2; groups x {xg} y {yl}/{yu}; c 0..{yc_top} "
      f"std band x >= {std_x0} ({std_band / 1e6:.3f} mm2 incl. above the stacks); std util at A={A:.0f}: "
      f"{A / std_band:.2f} of the band, {A / c_area:.2f} of c minus macros", file=sys.stderr)

# ------------------------------------------------------------------ lp.py spec (shared by both variants: same RTL)
lp = {
    "top": "dsdv_svc_attw_n1_f",
    "why": "ATTN1 (DRIVE-S81-ATTN1 10-20, G4 re-plan): narrowed attw (dsdv_svc_rs_attw1 at the production engine with "
           "NTP 1: ONE physical tile = 4 hard s81svc_attn_hgrp8 groups) -> landed parent: region c = the attention share "
           "(u_c), region t0 = the engine tile (u_t0). The c<->tile loop (issue -> tile -> lane re-assembly) is "
           "re-scheduled: schedule 'reference', ref TLX = TXD = 6 (+3 edges per landed crossing, both ways), landed TLX 6 / "
           "TXD 0.",
    "sources": [f"{D}/attw/dsdv_svc_attw_n1_f.sv"],
    "child_sources": SRC + HG_RTL,
    "include_dirs": [D],
    "defines": DEFS + ["OT_HGRP8_MOD=ot_s81svc8_hgrp_s81", "SVC8_WRITE_PREDECODE"],
    "params": dict(PAR, TLX=6, TXD=0),
    "ref_params": dict(PAR, TLX=6, TXD=6),
    "schedule": "reference",
    "out_dir": f"{D}/attw/lp",
    "record_dir": "results/arch/landed_parent_1018/dsdv_svc_attw_n1_f",
    "clock_ports": ["ck"],
    "clock_pins": ["ck", "clk"],
    "reset_port": "rst",
    "reset_pins": ["rst", "rst_n"],
    "static": ["sid"],
    "tb_static": {"sid": "4'd3"},
    "regions": regions,
    "bench": {"cycles": 6000, "reset_cycles": 24, "sim": "verilator"},
    "mut_child": "u_c",
}
if VAR == "main":
    (ROOT / "tools/landed_parent/specs/dsdv_svc_attw_n1_f.json").write_text(json.dumps(lp, indent=1) + "\n")

# ------------------------------------------------------------------ ref_tile kit spec (landed top)
ports_n = ["cs", "qrk", "qwd", "qrv", "qr_data", "qr_tag", "qr_beat", "qrq"]
ports_s = ["l_v", "l_d", "pv_ov", "pv_od", "sm_st", "sm_kind", "sm_jid", "sm_rv", "sm_rp", "sm_rj", "sm_rd",
           "go_o", "tjob_o", "done", "tagj", "hcr", "hack", "fault", "sid", "rst"]
name = f"dsdv_svc_attw_n1_{VAR}_lp"
kit = {
    "name": name,
    "top": "dsdv_svc_attw_n1_f_lp",
    "kind": "cluster",
    "sources": [f"{D}/attw/lp/dsdv_svc_attw_n1_f_lp.sv", f"{D}/attw/dsdv_svc_attw_n1_f.sv"] + SRC +
               ["rtl/common/landed_parent/ot_pl_land.sv"],
    "params": dict(PAR, TLX=6, TXD=0, MUT=0),
    "defines": DEFS,
    "orfs_vars": {"VERILOG_INCLUDE_DIRS": f"/src/{D}", "SYNTH_ARGS": "-noshare", "SYNTH_MEMORY_MAX_BITS": "163840"},
    "clock": "cts",
    "clock_port": "ck_c",
    "clock_ports": ["ck_c", "ck_t0"],
    "reset_ports": ["rst"],
    "sdc_extra": [f"{D}/attw/lp/dsdv_svc_attw_n1_f_lp.sdc"],
    "outline": {"w": W, "h": H},
    "cluster_level": 2,
    "children": ch,
    "macros": ms,
    "pins": {"N": ["ck_t0"] + ports_n, "S": ports_s[:len(ports_s) // 2] + ["ck_c"] + ports_s[len(ports_s) // 2:]},
    "recipe": 4,
    "hold_budget": "die",
    "route": {"pd": 0.5, "threads": 16, "peak_ram_gb": 256, "hold_margin_ns": 0.03, "io_hold_margin_ns": 0.03,
              "macro_halo_um": 5.4},
    "reset_landing": {"enable": True, "stages": 2},
    "pin_regs": {"enable": False, "reason": "source-registered: -DOT_SVC_ATT_PINREG registers every attw input pin "
                 "(q/hw/qr_*) and the fault OR; every other output is a dsdv_svc_att_core flop (SVC2 809c78aa5); "
                 "the c<->t0 crossing is a landing ring (owner 10-20 09:05: pin registers only at region crossings)"},
    "structural_change": f"ATTN1: narrowed attw (engine NTP 1, ONE tile region of 4 hard hgrp8 groups 2 x 2 + core region c, "
                         f"the tile bundle landed both ways, TLX 6); {VAR}: outline {W} x {H}",
}
(ROOT / f"tools/ref_tile/specs_s81dv_svc_lp/{name}.json").write_text(json.dumps(kit, indent=1) + "\n")
print(f"wrote {name}", file=sys.stderr)
